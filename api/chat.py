from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Query, status
from sqlalchemy.orm import Session
from db.crud import ChatService
from db.session import get_db
from schemas.chat import ChatSessionResponse, ChatMessageCreate, QuestionRequest
from schemas.graph_rag import ExtendedGraphRAGResponse
from utils.file_utils import save_chat_image
from typing import List, Optional
import json
from core.config import settings
import logging

from services.multimodal_rag_service import MultiModalRAGService
from services.llama_index_graph_rag import GraphRAGService
from services.auth.auth_service import get_user_from_token

logger = logging.getLogger(__name__)







router = APIRouter()

graph_rag_service = GraphRAGService()
multimodal_service = MultiModalRAGService(chroma_db_path=str(settings.CHROMA_DB_DIR))

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
async def get_all_chat_sessions(db: Session = Depends(get_db)):
    chat_service = ChatService(db)
    sessions = chat_service.get_all_chat_sessions()
    print(sessions)
    return [{"id": s.id, "created_at": s.created_at} for s in sessions]


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

        messages.append({
            "role": msg.role,
            "content": content,
            "images": images,
            "sources": sources,
            "created_at": msg.created_at,
        })

    return {
        "id": session.id,
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
    session_id: int,  # Change to int since that's what our DB uses
    request: QuestionRequest,
    mode: str = Query("normal", enum=["normal", "graph", "combined"]),
    db: Session = Depends(get_db)  # Add database dependency
):
    try:
        chat_service = ChatService(db)
        
        # Add user message to chat history
        chat_service.add_message_to_session(
            session_id=session_id,
            role="user",
            content=request.text
        )

        # Get response based on mode
        if mode == "normal":
            response = await multimodal_service.normal_query(request.text)
        elif mode == "graph":
            response = await graph_rag_service.get_answer(request.text)
        else:  # combined mode
            response = await multimodal_service.enhanced_query(request.text, top_k=4)

        # Format assistant response
        assistant_content = json.dumps({
            "answer": response.answer,
            "images": response.images if hasattr(response, "images") else [],
            "sources": response.sources if hasattr(response, "sources") else []
        })

        # Add assistant response to chat history
        chat_service.add_message_to_session(
            session_id=session_id,
            role="assistant",
            content=assistant_content
        )

        return response

    except Exception as e:
        logger.error(f"Error in ask_question: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def delete_chat_session(session_id: int, db: Session = Depends(get_db)):
    chat_service = ChatService(db)
    if chat_service.delete_chat_session(session_id):
        return {"status": "session deleted"}
    raise HTTPException(status_code=404, detail="Chat session not found")
