from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from db.session import get_db
from services.auth.auth_service import authenticate_user, create_access_token, get_password_hash, edit_profile, change_password, get_user_from_token
from db.models import User
from datetime import timedelta
from schemas.auth import UserRegisterDTO, UserLoginDTO, EditProfileDTO, ChangePasswordDTO

router = APIRouter()


@router.post("/register")
def register(user: UserRegisterDTO, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=user.email, 
        name=user.name, 
        hashed_password=hashed_password, 
        role=user.role,
        machine_name=user.machine_name,
        contradiction_tolerance=user.contradiction_tolerance,
        belief_sensitivity=user.belief_sensitivity
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "id": new_user.id, 
        "email": new_user.email, 
        "name": new_user.name, 
        "role": new_user.role,
        "machine_name": new_user.machine_name,
        "contradiction_tolerance": new_user.contradiction_tolerance,
        "belief_sensitivity": new_user.belief_sensitivity
    }

@router.post("/login")
def login(user: UserLoginDTO, db: Session = Depends(get_db)):
    auth_user = authenticate_user(db, user.email, user.password)
    if not auth_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access_token = create_access_token(
        data={"sub": auth_user.email},
        expires_delta=timedelta(minutes=30)
    )
    # Return user info without password
    user_data = {
        "id": auth_user.id, 
        "email": auth_user.email, 
        "name": auth_user.name, 
        "role": auth_user.role,
        "machine_name": auth_user.machine_name,
        "contradiction_tolerance": auth_user.contradiction_tolerance,
        "belief_sensitivity": auth_user.belief_sensitivity,
        "salience_decay_speed": auth_user.salience_decay_speed
    }
    return {"access_token": access_token, "token_type": "bearer", "user": user_data}

@router.post("/edit-profile")
def edit_profile_route(profile: EditProfileDTO, db: Session = Depends(get_db), user_id: int = None):
    # user_id should be extracted from token in real app
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    user = edit_profile(
        db, 
        user_id, 
        profile.name, 
        profile.machine_name, 
        profile.contradiction_tolerance, 
        profile.belief_sensitivity,
        profile.salience_decay_speed
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id, 
        "email": user.email, 
        "name": user.name, 
        "role": user.role,
        "machine_name": user.machine_name,
        "contradiction_tolerance": user.contradiction_tolerance,
        "belief_sensitivity": user.belief_sensitivity,
        "salience_decay_speed": user.salience_decay_speed
    }

@router.post("/change-password")
def change_password_route(data: ChangePasswordDTO, db: Session = Depends(get_db), user_id: int = None):
    # user_id should be extracted from token in real app
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")
    success, message = change_password(db, user_id, data.current_password, data.new_password, data.confirm_password)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@router.get("/me")
def get_current_user(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = auth_header.split(" ")[1]
    user, error = get_user_from_token(db, token)
    if error:
        raise HTTPException(status_code=401 if error == "Invalid token" else 404, detail=error)
    user_data = {
        "id": user.id, 
        "email": user.email, 
        "name": user.name, 
        "role": user.role,
        "machine_name": user.machine_name,
        "contradiction_tolerance": user.contradiction_tolerance,
        "belief_sensitivity": user.belief_sensitivity,
        "salience_decay_speed": user.salience_decay_speed
    }
    return user_data