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
)
from app.security.permissions import require_team_admin


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
    return ExpertRead.model_validate(expert)


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
    return ExpertRead.model_validate(updated_expert)


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
    return ExpertRead.model_validate(updated_expert)
