from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select
from typing import Dict, Any

from app.api.deps import get_db_session
from app.models.users import User
from app.models.team import Member
from app.security.passwords import verify_password
from app.security.jwt import create_access_token


router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    session: Session = Depends(get_db_session)
) -> LoginResponse:
    # Find user by email through Member relationship
    member = session.exec(select(Member).where(Member.email == request.email)).first()
    if not member:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Find user linked to this member
    user = session.exec(select(User).where(User.member_id == member.id)).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create JWT token
    access_token = create_access_token(user_id=user.id)
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer"
    ) 