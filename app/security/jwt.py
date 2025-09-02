import jwt as pyjwt
import datetime as dt
from typing import List
from pydantic import BaseModel
import os


class TokenData(BaseModel):
    sub: str  # user_id
    exp: int
    scopes: List[str] = []


def create_access_token(user_id: int, *, scopes: List[str] = None, expires_minutes: int = None) -> str:
    if scopes is None:
        scopes = []
    
    if expires_minutes is None:
        expires_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    expire = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=expires_minutes)
    
    payload = {
        "sub": str(user_id),
        "exp": int(expire.timestamp()),
        "scopes": scopes,
    }
    
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise ValueError("JWT_SECRET environment variable is required")
    
    algorithm = os.getenv("JWT_ALG", "HS256")
    
    return pyjwt.encode(payload, secret, algorithm=algorithm)


def decode_access_token(token: str) -> TokenData:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise ValueError("JWT_SECRET environment variable is required")
    
    algorithm = os.getenv("JWT_ALG", "HS256")
    
    try:
        payload = pyjwt.decode(token, secret, algorithms=[algorithm])
        return TokenData(**payload)
    except pyjwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except pyjwt.InvalidTokenError:
        raise ValueError("Invalid token") 