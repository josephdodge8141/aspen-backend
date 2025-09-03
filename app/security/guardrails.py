from fastapi import HTTPException
from sqlmodel import Session, select
from app.models.experts import Expert
from app.models.workflows import Workflow
from app.models.experts import ExpertService
from app.models.workflow_services import WorkflowService


def ensure_service_can_use_expert(
    session: Session, service_id: int, expert_id: int
) -> None:
    """
    Ensure that a service is allowed to use the specified expert.

    Raises:
        HTTPException: 404 if expert not found, 403 if service not linked
    """
    # First check if expert exists
    expert = session.get(Expert, expert_id)
    if expert is None:
        raise HTTPException(
            status_code=404,
            detail="Expert not found",
            headers={"Content-Type": "application/problem+json"},
        )

    # Check if service is linked to this expert
    statement = select(ExpertService).where(
        ExpertService.service_id == service_id, ExpertService.expert_id == expert_id
    )
    link = session.exec(statement).first()

    if link is None:
        raise HTTPException(
            status_code=403,
            detail="Service is not authorized to use this expert",
            headers={"Content-Type": "application/problem+json"},
        )


def ensure_service_can_use_workflow(
    session: Session, service_id: int, workflow_id: int
) -> None:
    """
    Ensure that a service is allowed to use the specified workflow.

    Raises:
        HTTPException: 404 if workflow not found, 403 if service not linked
    """
    # First check if workflow exists
    workflow = session.get(Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found",
            headers={"Content-Type": "application/problem+json"},
        )

    # Check if service is linked to this workflow
    statement = select(WorkflowService).where(
        WorkflowService.service_id == service_id,
        WorkflowService.workflow_id == workflow_id,
    )
    link = session.exec(statement).first()

    if link is None:
        raise HTTPException(
            status_code=403,
            detail="Service is not authorized to use this workflow",
            headers={"Content-Type": "application/problem+json"},
        )
