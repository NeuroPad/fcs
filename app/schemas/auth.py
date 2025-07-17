from typing import Optional
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict  # Include user information in the response


class TokenData(BaseModel):
    username: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserRegister(BaseModel):
    email: str
    name: str
    password: str
    machine_name: Optional[str] = None
    contradiction_tolerance: Optional[float] = None
    belief_sensitivity: Optional[str] = None