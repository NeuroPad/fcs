import os
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile
from sqlalchemy.orm import Session
from app.models.chat import ChatSession, ChatMessage


CHAT_IMAGES_DIR = Path("chat_images")
CHAT_IMAGES_DIR.mkdir(exist_ok=True)


# Define the path for storing chat images
CHAT_IMAGES_DIR = Path("chat_images")
CHAT_IMAGES_DIR.mkdir(exist_ok=True)


class ChatService:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_chat_session(self, user_id: int, title: str = None):
        new_session = ChatSession(user_id=user_id, title=title)
        self.db_session.add(new_session)
        self.db_session.commit()
        return new_session.id

    def get_chat_session(self, session_id: int):
        return (
            self.db_session.query(ChatSession)
            .filter(ChatSession.id == session_id)
            .first()
        )

    def get_all_chat_sessions(self):
        return self.db_session.query(ChatSession).all()
    
    def get_user_chat_sessions(self, user_id: int):
        return (
            self.db_session.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .order_by(ChatSession.created_at.desc())
            .all()
        )

    def add_message_to_session(
        self, session_id: int, role: str, content: str, image_path: str = None, nodes_referenced: list = None
    ):
        new_message = ChatMessage(
            session_id=session_id, 
            role=role, 
            content=content, 
            image_path=image_path,
            nodes_referenced=nodes_referenced
        )
        self.db_session.add(new_message)
        self.db_session.commit()
        return new_message

    def delete_chat_session(self, session_id: int):
        try:
            # First delete all messages associated with this session
            self.db_session.query(ChatMessage).filter(
                ChatMessage.session_id == session_id
            ).delete(synchronize_session=False)
            
            # Then delete the session
            session = (
                self.db_session.query(ChatSession)
                .filter(ChatSession.id == session_id)
                .first()
            )
            if session:
                self.db_session.delete(session)
            
            self.db_session.commit()
            return True
        except Exception as e:
            self.db_session.rollback()
            return False

    async def save_chat_image(self, image: UploadFile) -> str:
        """Save an uploaded image to the chat_images folder and return its path."""
        image_path = (
            CHAT_IMAGES_DIR / f"{datetime.utcnow().timestamp()}_{image.filename}"
        )
        with open(image_path, "wb") as buffer:
            buffer.write(await image.read())
        return str(image_path)
