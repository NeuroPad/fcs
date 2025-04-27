from pydantic import BaseModel

class UserRegisterDTO(BaseModel):
    email: str
    name: str
    password: str
    role: str = "user"

class UserLoginDTO(BaseModel):
    email: str
    password: str

class EditProfileDTO(BaseModel):
    name: str

class ChangePasswordDTO(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str