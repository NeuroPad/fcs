from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.role import Role, RoleCreate, RoleUpdate
from app.models.role import Role as RoleModel

router = APIRouter()


@router.get("/", response_model=List[Role])
def get_roles(db: Session = Depends(get_db)):
    """Get all roles."""
    roles = db.query(RoleModel).all()
    return roles


@router.post("/", response_model=Role)
def create_role(role_data: RoleCreate, db: Session = Depends(get_db)):
    """Create a new role."""
    # Check if role already exists
    existing_role = db.query(RoleModel).filter(RoleModel.name == role_data.name).first()
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role with this name already exists"
        )
    
    new_role = RoleModel(**role_data.dict())
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role


@router.get("/{role_id}", response_model=Role)
def get_role(role_id: int, db: Session = Depends(get_db)):
    """Get a specific role."""
    role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    return role


@router.put("/{role_id}", response_model=Role)
def update_role(role_id: int, role_data: RoleUpdate, db: Session = Depends(get_db)):
    """Update a specific role."""
    role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    update_data = role_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(role, key, value)
    
    db.commit()
    db.refresh(role)
    return role


@router.delete("/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db)):
    """Delete a specific role."""
    role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    db.delete(role)
    db.commit()
    return {"message": "Role deleted successfully"} 