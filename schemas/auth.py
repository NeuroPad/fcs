from pydantic import BaseModel

class UserRegisterDTO(BaseModel):
    email: str
    name: str
    password: str
    role: str = "user"
    machine_name: str = None
    contradiction_tolerance: float = None
    belief_sensitivity: str = None
    salience_decay_speed: str = "default"
    

class UserLoginDTO(BaseModel):
    email: str
    password: str

class EditProfileDTO(BaseModel):
    name: str
    machine_name: str = None
    contradiction_tolerance: float = None
    belief_sensitivity: str = None
    salience_decay_speed: str = "default"
    

class ChangePasswordDTO(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str