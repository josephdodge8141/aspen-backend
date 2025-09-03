from typing import Optional
from sqlmodel import SQLModel
from app.models.common import ExpertStatus


class ExpertBase(SQLModel):
    name: str
    prompt: str
    model_name: str
    status: ExpertStatus = ExpertStatus.draft
    input_params: dict


class ExpertCreate(ExpertBase):
    team_id: int


class ExpertUpdate(SQLModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    model_name: Optional[str] = None
    status: Optional[ExpertStatus] = None
    input_params: Optional[dict] = None


class ExpertRead(SQLModel):
    id: int
    uuid: str
    name: str
    prompt: str
    model_name: str
    status: ExpertStatus
    input_params: dict
    team_id: int


class ExpertListItem(SQLModel):
    id: int
    name: str
    model_name: str
    status: ExpertStatus
    prompt: str
    workflows_count: int
    services_count: int
    team_id: int
