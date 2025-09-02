from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session
from pydantic import BaseModel

from app.api.deps import get_db_session, get_current_user
from app.models.users import User
from app.models.experts import Expert, ExpertStatus
from app.schemas.experts import ExpertCreate, ExpertRead, ExpertUpdate, ExpertListItem
from app.repos.experts_repo import (
    create_expert,
    get_expert,
    update_expert,
    list_with_counts,
    get_with_expanded,
    add_expert_workflow_links,
    remove_expert_workflow_link,
    add_expert_service_links,
    remove_expert_service_link,
)
from app.security.permissions import require_team_admin
from app.services.templates import validate_template
from app.mappers.experts import to_read


class PreflightRequest(BaseModel):
    prompt: str
    input_params: Dict[str, Any]


class WorkflowLinksRequest(BaseModel):
    workflow_ids: List[int]


class ServiceLinksRequest(BaseModel):
    service_ids: List[int]


router = APIRouter(prefix="/api/v1/experts", tags=["Experts"])


@router.get("", response_model=List[ExpertListItem])
async def list_experts(
    team_id: Optional[int] = Query(None),
    status: Optional[List[ExpertStatus]] = Query(None),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> List[ExpertListItem]:
    """List experts with counts. Optionally filter by team_id and status."""
    return list_with_counts(session, team_id=team_id, status=status)


@router.post("", response_model=ExpertRead, status_code=201)
async def create_expert_endpoint(
    expert_data: ExpertCreate,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ExpertRead:
    """Create a new expert. Requires team admin permissions."""
    # Validate input_params is a dict
    if not isinstance(expert_data.input_params, dict):
        raise HTTPException(
            status_code=422,
            detail="input_params must be a JSON object",
            headers={"Content-Type": "application/problem+json"},
        )

    # Check team admin permission
    require_team_admin(session, current_user, expert_data.team_id)

    expert = create_expert(session, expert_data)
    return to_read(expert)


@router.get("/{expert_id}", response_model=Dict[str, Any])
async def get_expert_detailed(
    expert_id: int,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get expert with expanded workflows and services."""
    result = get_with_expanded(session, expert_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Expert not found")
    return result


@router.patch("/{expert_id}", response_model=ExpertRead)
async def update_expert_endpoint(
    expert_id: int,
    expert_data: ExpertUpdate,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ExpertRead:
    """Update an expert. Requires team admin permissions for the expert's team."""
    # Get current expert to check team
    expert = get_expert(session, expert_id)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")

    # Validate input_params is a dict if provided
    if expert_data.input_params is not None and not isinstance(
        expert_data.input_params, dict
    ):
        raise HTTPException(
            status_code=422,
            detail="input_params must be a JSON object",
            headers={"Content-Type": "application/problem+json"},
        )

    # Check team admin permission for current expert's team
    require_team_admin(session, current_user, expert.team_id)

    updated_expert = update_expert(session, expert_id, expert_data)
    return to_read(updated_expert)


@router.post("/{expert_id}:archive", response_model=ExpertRead)
async def archive_expert(
    expert_id: int,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ExpertRead:
    """Archive an expert. Requires team admin permissions for the expert's team."""
    # Get current expert to check team
    expert = get_expert(session, expert_id)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")

    # Check team admin permission for current expert's team
    require_team_admin(session, current_user, expert.team_id)

    # Archive is idempotent - if already archived, keep the status
    archive_data = ExpertUpdate(status=ExpertStatus.archive)
    updated_expert = update_expert(session, expert_id, archive_data)
    return to_read(updated_expert)


@router.post("/{expert_id}:preflight", response_model=Dict[str, Any])
async def preflight_expert_template(
    expert_id: int,
    request: PreflightRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Validate expert template prompt and input parameters."""
    # Check that expert exists (no need for team admin check since this is read-only validation)
    expert = get_expert(session, expert_id)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")

    # Validate the template
    result = validate_template(request.prompt, request.input_params)
    
    return result


@router.post("/{expert_id}/workflows", response_model=Dict[str, Any])
async def add_workflows_to_expert(
    expert_id: int,
    request: WorkflowLinksRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Add workflow links to an expert. Returns updated expanded view."""
    # Get current expert to check team
    expert = get_expert(session, expert_id)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")

    # Check team admin permission for current expert's team
    require_team_admin(session, current_user, expert.team_id)

    try:
        # Add workflow links and return expanded view
        return add_expert_workflow_links(session, expert_id, request.workflow_ids)
    except ValueError as e:
        if "Workflow with id" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{expert_id}/workflows/{workflow_id}", status_code=204)
async def remove_workflow_from_expert(
    expert_id: int,
    workflow_id: int,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a workflow link from an expert."""
    # Get current expert to check team
    expert = get_expert(session, expert_id)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")

    # Check team admin permission for current expert's team
    require_team_admin(session, current_user, expert.team_id)

    try:
        # Remove workflow link
        removed = remove_expert_workflow_link(session, expert_id, workflow_id)
        if not removed:
            # Link didn't exist, but that's fine for DELETE (idempotent)
            pass
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{expert_id}/services", response_model=Dict[str, Any])
async def add_services_to_expert(
    expert_id: int,
    request: ServiceLinksRequest,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Add service links to an expert. Returns updated expanded view."""
    # Get current expert to check team
    expert = get_expert(session, expert_id)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")

    # Check team admin permission for current expert's team
    require_team_admin(session, current_user, expert.team_id)

    try:
        # Add service links and return expanded view
        return add_expert_service_links(session, expert_id, request.service_ids)
    except ValueError as e:
        if "Service with id" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{expert_id}/services/{service_id}", status_code=204)
async def remove_service_from_expert(
    expert_id: int,
    service_id: int,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a service link from an expert."""
    # Get current expert to check team
    expert = get_expert(session, expert_id)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")

    # Check team admin permission for current expert's team
    require_team_admin(session, current_user, expert.team_id)

    try:
        # Remove service link
        removed = remove_expert_service_link(session, expert_id, service_id)
        if not removed:
            # Link didn't exist, but that's fine for DELETE (idempotent)
            pass
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
