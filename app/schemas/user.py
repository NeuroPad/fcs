from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    name: str
    is_active: Optional[bool] = True
    machine_name: Optional[str] = None
    contradiction_tolerance: Optional[float] = None
    belief_sensitivity: Optional[str] = None
    salience_decay_speed: Optional[str] = "default"


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None
    machine_name: Optional[str] = None
    contradiction_tolerance: Optional[float] = None
    belief_sensitivity: Optional[str] = None
    salience_decay_speed: Optional[str] = None


class UserInDBBase(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class User(UserInDBBase):
    pass


class UserInDB(UserInDBBase):
    hashed_password: str