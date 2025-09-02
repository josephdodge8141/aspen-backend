from typing import Optional
from sqlmodel import Field, Column
from sqlalchemy import JSON, LargeBinary, UniqueConstraint
from .common import TimestampMixin


class User(TimestampMixin, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: Optional[int] = Field(foreign_key="members.id", nullable=True)
    password_hash: Optional[str] = Field(nullable=True)
    service_user_id: Optional[int] = Field(foreign_key="service_users.id", nullable=True)


class ServiceUser(TimestampMixin, table=True):
    __tablename__ = "service_users"
    __table_args__ = (
        UniqueConstraint("segment_hash", name="uq_service_user_segment_hash"),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    segment_key: dict = Field(sa_column=Column(JSON, nullable=False))
    segment_hash: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    service_id: int = Field(foreign_key="services.id")
    version: int = Field() 