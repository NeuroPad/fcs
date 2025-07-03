from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import logging

from app.db.session import get_db
from app.core.config import settings
from app.services.chat_service import ChatService
from app.schemas.chat import ChatSessionResponse, ChatMessageCreate, QuestionRequest
from app.schemas.graph_rag import ExtendedGraphRAGResponse
from app.utils.file_utils import save_chat_image
from app.services.auth.auth_service import get_user_from_token
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)
router = APIRouter()


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
async def ask_question(
    session_id: int,
    request: QuestionRequest,
    mode: str = Query("normal", enum=["normal", "graph", "combined"]),
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
        
        # Get the session
        session = chat_service.get_chat_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Verify session belongs to authenticated user
        if session.user_id != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this chat session")
        
        # Get chat history for context
        chat_history = []
        for msg in session.messages:
            chat_history.append({
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at
            })
        
        # Add user message to chat history
        chat_service.add_message_to_session(
            session_id=session_id,
            role="user",
            content=request.text
        )
        
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
        
        return {"status": "success", "response": response_content}
        
    except Exception as e:
        logger.error(f"Error in ask_question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def delete_chat_session(session_id: int, db: Session = Depends(get_db)):
    chat_service = ChatService(db)
    try:
        chat_service.delete_chat_session(session_id)
        return {"status": "success", "message": "Chat session deleted"}
    except Exception as e:
        logger.error(f"Error deleting chat session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 