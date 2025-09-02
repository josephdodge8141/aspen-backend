from typing import Optional
from sqlmodel import Field
from sqlalchemy import UniqueConstraint
from .common import TimestampMixin, Environment


class Service(TimestampMixin, table=True):
    __tablename__ = "services"
    __table_args__ = (
        UniqueConstraint("name", "environment", name="uq_service_name_env"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field()
    environment: Environment = Field()
    api_key_hash: str = Field()  # Store hash only, not plaintext
    api_key_last4: str = Field(max_length=4)  # Last 4 digits for display


class ServiceSegment(TimestampMixin, table=True):
    __tablename__ = "service_segments"
    __table_args__ = (
        UniqueConstraint("service_id", "name", name="uq_service_segment_name"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    service_id: int = Field(foreign_key="services.id")
    name: str = Field()  # Named segment schemas
