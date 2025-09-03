from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field
from app.models.common import NodeType


class WorkflowBase(SQLModel):
    name: str
    description: Optional[str] = None
    input_params: Dict[str, Any] = Field(default_factory=dict)
    is_api: bool = False
    cron_schedule: Optional[str] = None
    team_id: int


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    input_params: Optional[Dict[str, Any]] = None
    is_api: Optional[bool] = None
    cron_schedule: Optional[str] = None


class WorkflowListItem(SQLModel):
    id: int
    uuid: str
    name: str
    description_truncated: Optional[str]
    experts: List[Dict[str, Any]]  # [{"id": int, "name": str}] (first 5)
    experts_count: int
    services_count: int


class WorkflowRead(SQLModel):
    id: int
    uuid: str
    name: str
    description: Optional[str]
    input_params: Dict[str, Any]
    is_api: bool
    cron_schedule: Optional[str]
    team_id: int


class NodeCreate(SQLModel):
    node_type: NodeType
    node_metadata: Dict[str, Any] = Field(default_factory=dict)
    structured_output: Dict[str, Any] = Field(default_factory=dict)


class NodeUpdate(SQLModel):
    node_type: Optional[NodeType] = None
    node_metadata: Optional[Dict[str, Any]] = None
    structured_output: Optional[Dict[str, Any]] = None


class NodeRead(SQLModel):
    id: int
    node_type: NodeType
    node_metadata: Dict[str, Any]
    structured_output: Dict[str, Any]


class EdgeCreate(SQLModel):
    parent_id: int
    child_id: int
    branch_label: Optional[str] = None


class EdgeRead(SQLModel):
    id: int
    parent_id: int
    child_id: int
    branch_label: Optional[str]
