from typing import Optional
from sqlmodel import Field, Column
from sqlalchemy import Index, UniqueConstraint, Text, JSON
import uuid as uuid_lib
from .common import TimestampMixin, ExpertStatus


class Expert(TimestampMixin, table=True):
    __tablename__ = "experts"
    __table_args__ = (
        Index("idx_experts_team_id", "team_id"),
        Index("idx_experts_status", "status"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: str = Field(default_factory=lambda: str(uuid_lib.uuid4()), unique=True)
    prompt: str = Field(sa_column=Column(Text, nullable=False))
    name: str = Field()
    model_name: str = Field()
    status: ExpertStatus = Field()
    input_params: Optional[dict] = Field(sa_column=Column(JSON, nullable=True))
    team_id: int = Field(foreign_key="teams.id")


class ExpertService(TimestampMixin, table=True):
    __tablename__ = "expert_services"
    __table_args__ = (
        UniqueConstraint("expert_id", "service_id", name="uq_expert_service"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    expert_id: int = Field(foreign_key="experts.id")
    service_id: int = Field()  # FK to services.id - will be added later


class ExpertWorkflow(TimestampMixin, table=True):
    __tablename__ = "expert_workflows"
    __table_args__ = (
        UniqueConstraint("expert_id", "workflow_id", name="uq_expert_workflow"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    expert_id: int = Field(foreign_key="experts.id")
    workflow_id: int = Field()  # FK to workflows.id - will be added later
