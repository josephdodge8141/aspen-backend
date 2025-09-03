from sqlmodel import SQLModel
from app.models.common import Environment


class ServiceBase(SQLModel):
    name: str
    environment: Environment


class ServiceCreate(ServiceBase):
    pass


class ServiceRead(SQLModel):
    id: int
    name: str
    environment: Environment
    api_key_last4: str | None = None


class ServiceRotateKeyRead(SQLModel):
    id: int
    name: str
    environment: Environment
    api_key_plaintext: str  # ONLY on rotation response
    api_key_last4: str


class ServiceSegmentBase(SQLModel):
    name: str


class ServiceSegmentCreate(ServiceSegmentBase):
    pass


class ServiceSegmentRead(SQLModel):
    id: int
    service_id: int
    name: str 