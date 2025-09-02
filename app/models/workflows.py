from typing import Optional
from sqlmodel import Field, Column, CheckConstraint
from sqlalchemy import JSON, UniqueConstraint, Text
import uuid as uuid_lib
from .common import TimestampMixin, NodeType


class Workflow(TimestampMixin, table=True):
    __tablename__ = "workflows"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: str = Field(default_factory=lambda: str(uuid_lib.uuid4()), unique=True)
    name: str = Field(nullable=False)
    description: Optional[str] = Field(sa_column=Column(Text, nullable=True))
    input_params: Optional[dict] = Field(sa_column=Column(JSON, nullable=True))
    is_api: bool = Field(default=False, nullable=False)
    cron_schedule: Optional[str] = Field(nullable=True)
    team_id: int = Field(foreign_key="teams.id", nullable=False)


class Node(TimestampMixin, table=True):
    __tablename__ = "nodes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: int = Field(foreign_key="workflows.id", nullable=False)
    node_type: NodeType = Field(nullable=False)
    node_metadata: Optional[dict] = Field(sa_column=Column(JSON, nullable=True))
    structured_output: Optional[dict] = Field(sa_column=Column(JSON, nullable=True))


class NodeNode(TimestampMixin, table=True):
    __tablename__ = "node_nodes"
    __table_args__ = (
        UniqueConstraint("parent_id", "child_id", name="uq_node_edge_pair"),
        CheckConstraint("parent_id != child_id", name="chk_no_self_edge"),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    parent_id: int = Field(foreign_key="nodes.id", nullable=False)
    child_id: int = Field(foreign_key="nodes.id", nullable=False) 