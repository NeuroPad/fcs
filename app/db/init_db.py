from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from passlib.context import CryptContext
import logging

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_db_and_tables():
    """Create database tables."""
    Base.metadata.create_all(bind=engine)


def init_db(db: Session) -> None:
    """Initialize database with default data."""
    # Check if roles already exist
    if not db.query(Role).filter(Role.name == "admin").first():
        admin_role = Role(name="admin", description="Administrator role")
        db.add(admin_role)
        
    if not db.query(Role).filter(Role.name == "user").first():
        user_role = Role(name="user", description="Regular user role")
        db.add(user_role)
        
    db.commit()
    logger.info("Database initialized with default roles")


def create_admin_user(db: Session, email: str, password: str, name: str = "Admin") -> User:
    """Create an admin user."""
    # Check if admin user already exists
    admin_user = db.query(User).filter(User.email == email).first()
    if admin_user:
        logger.info(f"Admin user {email} already exists")
        return admin_user
    
    # Get admin role
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        logger.error("Admin role not found. Run init_db first.")
        return None
    
    # Create admin user
    hashed_password = pwd_context.hash(password)
    admin_user = User(
        email=email,
        name=name,
        hashed_password=hashed_password,
        is_active=True
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    # Assign admin role
    user_role = UserRole(user_id=admin_user.id, role_id=admin_role.id)
    db.add(user_role)
    db.commit()
    
    logger.info(f"Admin user {email} created successfully")
    return admin_user


def main():
    """Main initialization function."""
    logger.info("Creating database tables...")
    create_db_and_tables()
    
    db = SessionLocal()
    try:
        logger.info("Initializing database with default data...")
        init_db(db)
        
        # Create default admin user if specified in environment
        admin_email = "admin@memduo.com"  # Change this
        admin_password = "admin123"  # Change this in production
        create_admin_user(db, admin_email, admin_password, "System Admin")
        
    finally:
        db.close()


if __name__ == "__main__":
    main() 