from sqlalchemy.orm import Session
from db.models import ChatSession, ChatMessage


class ChatService:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_chat_session(self):
        new_session = ChatSession()
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

    def add_message_to_session(
        self, session_id: int, role: str, content: str, image_path: str = None
    ):
        new_message = ChatMessage(
            session_id=session_id, role=role, content=content, image_path=image_path
        )
        self.db_session.add(new_message)
        self.db_session.commit()
        return new_message

    def delete_chat_session(self, session_id: int):
        session = (
            self.db_session.query(ChatSession)
            .filter(ChatSession.id == session_id)
            .first()
        )
        if session:
            self.db_session.delete(session)
            self.db_session.commit()
            return True
        return False
