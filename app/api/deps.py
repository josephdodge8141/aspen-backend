from typing import Optional
from fastapi import Header, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from pydantic import BaseModel

from app.database import engine
from app.models.users import User
from app.models.services import Service
from app.security.jwt import decode_access_token
from app.security.apikeys import hash_api_key


class CallerContext(BaseModel):
    service: Optional[Service] = None
    user: Optional[User] = None


def get_db_session() -> Session:
    with Session(engine) as session:
        yield session


security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    session: Session = Depends(get_db_session),
) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authorization token required")

    try:
        token_data = decode_access_token(credentials.credentials)
        user_id = int(token_data.sub)

        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


async def get_caller(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
    session: Session = Depends(get_db_session),
) -> CallerContext:
    context = CallerContext()

    # Prefer JWT for admin endpoints over X-API-Key
    # If Authorization Bearer present, resolve User (higher priority)
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]  # Remove "Bearer " prefix
        try:
            token_data = decode_access_token(token)
            user_id = int(token_data.sub)

            user = session.get(User, user_id)
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="User not found",
                    headers={"Content-Type": "application/problem+json"},
                )
            context.user = user
        except ValueError as e:
            raise HTTPException(
                status_code=401,
                detail=str(e),
                headers={"Content-Type": "application/problem+json"},
            )

    # If X-API-Key present and no JWT, resolve Service
    elif x_api_key:
        api_key_hash = hash_api_key(x_api_key)
        service = session.exec(
            select(Service).where(Service.api_key_hash == api_key_hash)
        ).first()
        if not service:
            raise HTTPException(
                status_code=401,
                detail="Invalid API key",
                headers={"Content-Type": "application/problem+json"},
            )
        context.service = service
    else:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"Content-Type": "application/problem+json"},
        )

    return context
