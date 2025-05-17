from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from db.session import get_db
from services.auth.auth_service import authenticate_user, create_access_token, get_password_hash, edit_profile, change_password
from .auth.jwt_handler import get_current_active_user
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
        expires_delta=timedelta(days=30)
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
def edit_profile_route(profile: EditProfileDTO, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    user_id = current_user.id
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
def change_password_route(data: ChangePasswordDTO, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    user_id = current_user.id
    success, message = change_password(db, user_id, data.current_password, data.new_password, data.confirm_password)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@router.get("/me")
def get_current_user_route(current_user: User = Depends(get_current_active_user)):
    user = current_user
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