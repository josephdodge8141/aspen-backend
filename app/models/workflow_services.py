from typing import Optional
from sqlmodel import Field
from sqlalchemy import UniqueConstraint
from .common import TimestampMixin


class WorkflowService(TimestampMixin, table=True):
    __tablename__ = "workflow_services"
    __table_args__ = (
        UniqueConstraint("workflow_id", "service_id", name="uq_workflow_service"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: int = Field(foreign_key="workflows.id", nullable=False)
    service_id: int = Field(foreign_key="services.id", nullable=False)
