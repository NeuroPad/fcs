from pydantic import BaseModel
from .user import User
from .role import Role


class UserRoleBase(BaseModel):
    user_id: int
    role_id: int


class UserRoleCreate(UserRoleBase):
    pass


class UserRoleInDBBase(UserRoleBase):
    class Config:
        from_attributes = True


class UserRole(UserRoleInDBBase):
    user: User
    role: Role 