from app.db.session import Base

# Import all models here to ensure they are registered with SQLAlchemy
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole
from app.models.chat import ChatSession, ChatMessage
from app.models.document import Document 