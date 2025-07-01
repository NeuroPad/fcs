from typing import Optional
from pydantic import BaseModel


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RoleInDBBase(RoleBase):
    id: int

    class Config:
        from_attributes = True


class Role(RoleInDBBase):
    pass 