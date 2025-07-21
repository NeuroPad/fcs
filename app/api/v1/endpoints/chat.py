from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Query, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
import json
import logging
import json
import hashlib
import time
from datetime import datetime
from functools import wraps

from app.db.session import get_db
from app.core.config import settings
from app.services.chat_service import ChatService
from app.schemas.chat import ChatSessionResponse, ChatMessageCreate, QuestionRequest
from app.schemas.graph_rag import ExtendedGraphRAGResponse
from app.utils.file_utils import save_chat_image
from app.services.auth.auth_service import get_user_from_token
from app.services.rag_service import RAGService
from app.models.chat import ChatMessage

logger = logging.getLogger(__name__)

# Performance monitoring decorator
def monitor_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"{func.__name__} completed in {duration:.2f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} failed after {duration:.2f}s: {e}")
            raise
    return wrapper

# Import Redis cache service
from app.services.cache_service import chat_cache

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint with performance metrics"""
    try:
        cache_stats = chat_cache.get_stats()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "cache": cache_stats,
            "performance": {
                "cache_enabled": cache_stats.get("status") == "connected",
                "optimizations_active": True
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "degraded",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }


async def get_base_url(request: Request) -> str:
    return str(request.base_url).rstrip('/')

@router.post("/new", response_model=ChatSessionResponse)
async def create_new_chat(
    request: Request,
    title: str = Form(None),
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = auth_header.split(" ")[1]
    user, error = get_user_from_token(db, token)
    if error:
        raise HTTPException(status_code=401 if error == "Invalid token" else 404, detail=error)
    chat_service = ChatService(db)
    session_id = chat_service.create_chat_session(user_id=user.id, title=title)
    session = chat_service.get_chat_session(session_id)
    return {
        "id": session.id,
        "user_id": session.user_id,
        "title": session.title,
        "created_at": session.created_at,
        "messages": []
    }


@router.get("/sessions")
async def get_all_chat_sessions(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = auth_header.split(" ")[1]
    user, error = get_user_from_token(db, token)
    if error:
        raise HTTPException(status_code=401 if error == "Invalid token" else 404, detail=error)
    chat_service = ChatService(db)
    sessions = chat_service.get_user_chat_sessions(user.id)
    return [{"id": s.id, "created_at": s.created_at, "title": s.title} for s in sessions]


@router.get("/session/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    chat_service = ChatService(db)
    session = chat_service.get_chat_session(session_id)
    base_url = await get_base_url(request)

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = []
    for msg in session.messages:
        content = msg.content
        images = []
        sources = []

        if msg.role == "assistant":
            try:
                parsed_content = json.loads(msg.content)
                content = parsed_content.get("answer", msg.content)

                if parsed_content.get("images"):
                    images = [f"{base_url}/{img}" for img in parsed_content["images"]]

                if parsed_content.get("sources"):
                    sources = [
                        f'<a href="{base_url}/{src}" target="_blank" style="color: white;" download>{src}</a>'
                        for src in parsed_content["sources"]
                    ]

            except json.JSONDecodeError:
                pass

        # Extract reasoning nodes if available
        reasoning_nodes = []
        if msg.nodes_referenced:
            try:
                reasoning_nodes = msg.nodes_referenced if isinstance(msg.nodes_referenced, list) else []
            except Exception as e:
                logger.warning(f"Error parsing reasoning nodes: {e}")

        messages.append({
            "role": msg.role,
            "content": content,
            "images": images,
            "sources": sources,
            "reasoning_nodes": reasoning_nodes,
            "created_at": msg.created_at,
        })

    return {
        "id": session.id,
        "user_id": session.user_id,
        "title": session.title,
        "created_at": session.created_at,
        "messages": messages
    }


@router.post("/session/{session_id}/message")
async def add_message_to_chat(
    session_id: int,
    role: str,
    content: str = None,
    image: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    chat_service = ChatService(db)
    if role not in ["user", "assistant"]:
        raise HTTPException(
            status_code=400, detail="Role must be 'user' or 'assistant'"
        )

    image_path = None
    if image:
        image_path = await save_chat_image(image)

    chat_service.add_message_to_session(session_id, role, content, image_path)
    return {"status": "message added", "image_path": image_path}


@router.post("/session/{session_id}/ask")
@monitor_performance
async def ask_question(
    session_id: int,
    request: QuestionRequest,
    background_tasks: BackgroundTasks,
    mode: str = Query("normal", description="Query mode: normal, graph, or combined"),
    db: Session = Depends(get_db),
    current_request: Request = None
):
    try:
        chat_service = ChatService(db)
        
        # Get user from token
        auth_header = current_request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Not authenticated")
        token = auth_header.split(" ")[1]
        user, error = get_user_from_token(db, token)
        if error:
            raise HTTPException(status_code=401 if error == "Invalid token" else 404, detail=error)
        
        # Check cache first
        cached_response = chat_cache.get_chat_response(request.text, user.id, mode)
        if cached_response:
            logger.info(f"Cache hit for user {user.id}, query: {request.text[:50]}...")
            return cached_response
        
        # Get the session with optimized query
        session = chat_service.get_chat_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Verify session belongs to authenticated user
        if session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this chat session")
        
        # Get chat history for context (limit to last 10 messages for performance)
        chat_history = []
        recent_messages = sorted(session.messages, key=lambda x: x.created_at)[-10:]
        for msg in recent_messages:
            chat_history.append({
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at
            })
        
        # We'll add user message only after successful processing
        
        # Add the current message to chat history for context
        chat_history.append({"role": "user", "content": request.text})
        
        # Create user object with id and name
        user_obj = {
            'id': str(user.id),
            'name': user.name or f"User {user.id}",
            'machine_name': user.machine_name or "Assistant",
            'contradiction_tolerance': user.contradiction_tolerance or 0,
            'belief_sensitivity': user.belief_sensitivity or "moderate",
            'salience_decay_speed': user.salience_decay_speed or "default"
        }
        
        # Initialize RAG service
        rag_service = RAGService()
        
        # Process based on mode
        try:
            if mode == "graph":
                from app.services.llama_index_graph_rag import GraphRAGService
                graph_rag_service = GraphRAGService()
                answer_data = await graph_rag_service.get_answer(request.text, chat_history, user_obj)
                response_content = json.dumps({
                    "answer": answer_data.answer,
                    "reasoning_nodes": [node.dict() for node in answer_data.reasoning_nodes] if answer_data.reasoning_nodes else [],
                    "sources": answer_data.sources or []
                })
            elif mode == "combined":
                # Use both RAG and Graph RAG
                normal_result = await rag_service.query(request.text, user.id, chat_history=chat_history, user=user_obj)
                from app.services.llama_index_graph_rag import GraphRAGService
                graph_rag_service = GraphRAGService()
                graph_result = await graph_rag_service.get_answer(request.text, chat_history, user_obj)
                
                response_content = json.dumps({
                    "answer": f"Combined Response:\n\nRAG: {normal_result.answer if normal_result.answer else ''}\n\nGraph RAG: {graph_result.answer}",
                    "reasoning_nodes": [node.dict() for node in graph_result.reasoning_nodes] if graph_result.reasoning_nodes else [],
                    "sources": (normal_result.sources or []) + (graph_result.sources or [])
                })
            else:
                # Normal RAG mode
                result = await rag_service.query(request.text, user.id, chat_history=chat_history, user=user_obj)
                response_content = json.dumps({
                    "answer": result.answer if result.answer else 'No answer found',
                    "sources": result.sources if result.sources else [],
                    "reasoning_nodes": [node.dict() for node in result.reasoning_nodes] if result.reasoning_nodes else []
                })
            
            # Check if the response contains quota errors even if wrapped in success
            try:
                parsed_response = json.loads(response_content)
                answer_text = parsed_response.get("answer", "")
                
                # Check for quota errors in the answer text
                if ("insufficient_quota" in answer_text.lower() or 
                    "quota" in answer_text.lower() or
                    "Error code: 429" in answer_text or
                    "exceeded your current quota" in answer_text.lower()):
                    
                    # Return elegant error response without saving anything
                    error_response = json.dumps({
                        "answer": "💡 AI service quota exceeded. Your request couldn't be processed due to usage limits. Please try again in a few moments or contact support if this persists.",
                        "sources": [],
                        "reasoning_nodes": []
                    })
                    return {"status": "success", "response": error_response}
                    
            except json.JSONDecodeError:
                pass  # If we can't parse the JSON, continue with normal flow
            
            # Only save to database if no errors detected
            # Add user message to chat history
            chat_service.add_message_to_session(
                session_id=session_id,
                role="user",
                content=request.text
            )
            
            # Extract reasoning nodes from response content for storage
            nodes_referenced = []
            try:
                parsed_response = json.loads(response_content)
                if parsed_response.get("reasoning_nodes"):
                    nodes_referenced = parsed_response["reasoning_nodes"]
            except (json.JSONDecodeError, KeyError):
                pass
            
            # Add assistant response to chat
            chat_service.add_message_to_session(
                session_id=session_id,
                role="assistant",
                content=response_content,
                nodes_referenced=nodes_referenced
            )
            
            # Cache the response
            response_data = {"status": "success", "response": response_content}
            chat_cache.set_chat_response(request.text, user.id, mode, response_data)
            
            return response_data
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"LLM query error: {error_message}")
            
            # For quota errors, rate limits, and timeouts, return elegant error responses without saving
            if "insufficient_quota" in error_message.lower() or "quota" in error_message.lower():
                error_response = json.dumps({
                    "answer": "💡 AI service quota exceeded. Your request couldn't be processed due to usage limits. Please try again in a few moments or contact support if this persists.",
                    "sources": [],
                    "reasoning_nodes": []
                })
                return {"status": "success", "response": error_response}
                
            elif "rate_limit" in error_message.lower() or "rate limit" in error_message.lower():
                error_response = json.dumps({
                    "answer": "⏱️ Too many requests detected. Please slow down and try again in a few seconds.",
                    "sources": [],
                    "reasoning_nodes": []
                })
                return {"status": "success", "response": error_response}
                
            elif "timeout" in error_message.lower():
                error_response = json.dumps({
                    "answer": "⏰ Request timed out. The AI service is taking longer than expected. Please try again.",
                    "sources": [],
                    "reasoning_nodes": []
                })
                return {"status": "success", "response": error_response}
                
            else:
                # For other errors, return generic error without saving
                error_response = json.dumps({
                    "answer": "🔧 Something went wrong on our end. Please try again or contact support if the issue persists.",
                    "sources": [],
                    "reasoning_nodes": []
                })
                return {"status": "success", "response": error_response}
        
    except Exception as e:
        # This outer exception handler catches errors not related to LLM calls
        # such as database errors, authentication issues, etc.
        logger.error(f"Unexpected error in ask_question: {str(e)}")
        error_response = json.dumps({
            "answer": "🔧 Something went wrong on our end. Please try again or contact support if the issue persists.",
            "sources": [],
            "reasoning_nodes": []
        })
        return {"status": "success", "response": error_response}


@router.delete("/session/{session_id}")
async def delete_chat_session(session_id: int, db: Session = Depends(get_db)):
    chat_service = ChatService(db)
    try:
        chat_service.delete_chat_session(session_id)
        return {"status": "success", "message": "Chat session deleted"}
    except Exception as e:
        logger.error(f"Error deleting chat session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))