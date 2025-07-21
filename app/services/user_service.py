from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.user import User as UserModel
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_users(self, skip: int = 0, limit: int = 100) -> List[UserModel]:
        """Get all users with pagination."""
        return self.db.query(UserModel).offset(skip).limit(limit).all()

    def get_user(self, user_id: int) -> Optional[UserModel]:
        """Get a user by ID."""
        return self.db.query(UserModel).filter(UserModel.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        """Get a user by email."""
        return self.db.query(UserModel).filter(UserModel.email == email).first()

    def create_user(self, user_data: UserCreate) -> UserModel:
        """Create a new user."""
        db_user = UserModel(
            email=user_data.email,
            name=user_data.name,
            hashed_password=user_data.password,  # Note: This should be hashed in auth service
            is_active=True,
            machine_name=user_data.machine_name,
            contradiction_tolerance=user_data.contradiction_tolerance,
            belief_sensitivity=user_data.belief_sensitivity,
            salience_decay_speed=user_data.salience_decay_speed
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def update_user(self, user_id: int, user_update: UserUpdate) -> Optional[UserModel]:
        """Update a user."""
        db_user = self.get_user(user_id)
        if not db_user:
            return None

        update_data = user_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_user, field, value)

        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        db_user = self.get_user(user_id)
        if not db_user:
            return False

        self.db.delete(db_user)
        self.db.commit()
        return True

    def activate_user(self, user_id: int) -> Optional[UserModel]:
        """Activate a user."""
        db_user = self.get_user(user_id)
        if not db_user:
            return None

        db_user.is_active = True
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def deactivate_user(self, user_id: int) -> Optional[UserModel]:
        """Deactivate a user."""
        db_user = self.get_user(user_id)
        if not db_user:
            return None

        db_user.is_active = False
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def get_active_users(self, skip: int = 0, limit: int = 100) -> List[UserModel]:
        """Get all active users."""
        return (
            self.db.query(UserModel)
            .filter(UserModel.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search_users(self, query: str, skip: int = 0, limit: int = 100) -> List[UserModel]:
        """Search users by name or email."""
        return (
            self.db.query(UserModel)
            .filter(
                and_(
                    UserModel.name.ilike(f"%{query}%") |
                    UserModel.email.ilike(f"%{query}%")
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )