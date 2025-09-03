from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_db_session, get_caller, CallerContext
from app.security.apikeys import generate_api_key
from app.models.services import Service, ServiceSegment
from app.models.experts import Expert, ExpertService
from app.models.workflows import Workflow
from app.models.workflow_services import WorkflowService
from app.schemas.services import (
    ServiceCreate,
    ServiceRead,
    ServiceRotateKeyRead,
    ServiceSegmentCreate,
    ServiceSegmentRead,
)


router = APIRouter(prefix="/api/v1/services", tags=["Services"])


@router.post("", response_model=ServiceRotateKeyRead)
def create_service(
    service_data: ServiceCreate,
    session: Session = Depends(get_db_session),
    caller: CallerContext = Depends(get_caller),
):
    plaintext_key, api_key_hash, last4 = generate_api_key()
    
    service = Service(
        name=service_data.name,
        environment=service_data.environment,
        api_key_hash=api_key_hash,
        api_key_last4=last4,
    )
    
    try:
        session.add(service)
        session.commit()
        session.refresh(service)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Service with name '{service_data.name}' already exists in {service_data.environment} environment",
        )
    
    return ServiceRotateKeyRead(
        id=service.id,
        name=service.name,
        environment=service.environment,
        api_key_plaintext=plaintext_key,
        api_key_last4=service.api_key_last4,
    )


@router.get("", response_model=List[ServiceRead])
def list_services(
    session: Session = Depends(get_db_session),
    caller: CallerContext = Depends(get_caller),
):
    statement = select(Service)
    services = session.exec(statement).all()
    
    return [
        ServiceRead(
            id=service.id,
            name=service.name,
            environment=service.environment,
            api_key_last4=service.api_key_last4,
        )
        for service in services
    ]


@router.get("/{service_id}", response_model=ServiceRead)
def get_service(
    service_id: int,
    session: Session = Depends(get_db_session),
    caller: CallerContext = Depends(get_caller),
):
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )
    
    return ServiceRead(
        id=service.id,
        name=service.name,
        environment=service.environment,
        api_key_last4=service.api_key_last4,
    )


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: int,
    session: Session = Depends(get_db_session),
    caller: CallerContext = Depends(get_caller),
):
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )
    
    session.delete(service)
    session.commit()


@router.post("/{service_id}:rotate-key", response_model=ServiceRotateKeyRead)
def rotate_service_key(
    service_id: int,
    session: Session = Depends(get_db_session),
    caller: CallerContext = Depends(get_caller),
):
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )
    
    plaintext_key, api_key_hash, last4 = generate_api_key()
    
    service.api_key_hash = api_key_hash
    service.api_key_last4 = last4
    
    session.add(service)
    session.commit()
    session.refresh(service)
    
    return ServiceRotateKeyRead(
        id=service.id,
        name=service.name,
        environment=service.environment,
        api_key_plaintext=plaintext_key,
        api_key_last4=service.api_key_last4,
    )


# Service Segments endpoints
@router.post("/{service_id}/segments", response_model=ServiceSegmentRead)
def create_service_segment(
    service_id: int,
    segment_data: ServiceSegmentCreate,
    session: Session = Depends(get_db_session),
    caller: CallerContext = Depends(get_caller),
):
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )
    
    segment = ServiceSegment(
        service_id=service_id,
        name=segment_data.name,
    )
    
    try:
        session.add(segment)
        session.commit()
        session.refresh(segment)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Segment with name '{segment_data.name}' already exists for this service",
        )
    
    return ServiceSegmentRead(
        id=segment.id,
        service_id=segment.service_id,
        name=segment.name,
    )


@router.get("/{service_id}/segments", response_model=List[ServiceSegmentRead])
def list_service_segments(
    service_id: int,
    session: Session = Depends(get_db_session),
    caller: CallerContext = Depends(get_caller),
):
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )
    
    statement = select(ServiceSegment).where(ServiceSegment.service_id == service_id)
    segments = session.exec(statement).all()
    
    return [
        ServiceSegmentRead(
            id=segment.id,
            service_id=segment.service_id,
            name=segment.name,
        )
        for segment in segments
    ]


@router.delete("/{service_id}/segments/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_segment(
    service_id: int,
    segment_id: int,
    session: Session = Depends(get_db_session),
    caller: CallerContext = Depends(get_caller),
):
    statement = select(ServiceSegment).where(
        ServiceSegment.id == segment_id,
        ServiceSegment.service_id == service_id,
    )
    segment = session.exec(statement).first()
    
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segment not found",
        )
    
    session.delete(segment)
    session.commit()


# Service linking endpoints
from pydantic import BaseModel

class LinkExpertsRequest(BaseModel):
    expert_ids: List[int]

class LinkWorkflowsRequest(BaseModel):
    workflow_ids: List[int]

class LinkResponse(BaseModel):
    linked: List[int]


@router.post("/{service_id}/experts", response_model=LinkResponse)
def link_service_to_experts(
    service_id: int,
    request: LinkExpertsRequest,
    session: Session = Depends(get_db_session),
    caller: CallerContext = Depends(get_caller),
):
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )
    
    # Check that all experts exist
    expert_statement = select(Expert).where(Expert.id.in_(request.expert_ids))
    existing_experts = session.exec(expert_statement).all()
    existing_expert_ids = {expert.id for expert in existing_experts}
    
    missing_ids = set(request.expert_ids) - existing_expert_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experts not found: {list(missing_ids)}",
        )
    
    # Get existing links to avoid duplicates
    existing_links_statement = select(ExpertService).where(
        ExpertService.service_id == service_id,
        ExpertService.expert_id.in_(request.expert_ids),
    )
    existing_links = session.exec(existing_links_statement).all()
    existing_expert_ids_linked = {link.expert_id for link in existing_links}
    
    # Create new links
    new_links = []
    for expert_id in request.expert_ids:
        if expert_id not in existing_expert_ids_linked:
            new_links.append(ExpertService(expert_id=expert_id, service_id=service_id))
    
    if new_links:
        session.add_all(new_links)
        session.commit()
    
    # Return all linked expert IDs
    all_links_statement = select(ExpertService).where(ExpertService.service_id == service_id)
    all_links = session.exec(all_links_statement).all()
    
    return LinkResponse(linked=[link.expert_id for link in all_links])


@router.delete("/{service_id}/experts/{expert_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_service_from_expert(
    service_id: int,
    expert_id: int,
    session: Session = Depends(get_db_session),
    caller: CallerContext = Depends(get_caller),
):
    statement = select(ExpertService).where(
        ExpertService.service_id == service_id,
        ExpertService.expert_id == expert_id,
    )
    link = session.exec(statement).first()
    
    if link:
        session.delete(link)
        session.commit()


@router.post("/{service_id}/workflows", response_model=LinkResponse)
def link_service_to_workflows(
    service_id: int,
    request: LinkWorkflowsRequest,
    session: Session = Depends(get_db_session),
    caller: CallerContext = Depends(get_caller),
):
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )
    
    # Check that all workflows exist
    workflow_statement = select(Workflow).where(Workflow.id.in_(request.workflow_ids))
    existing_workflows = session.exec(workflow_statement).all()
    existing_workflow_ids = {workflow.id for workflow in existing_workflows}
    
    missing_ids = set(request.workflow_ids) - existing_workflow_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflows not found: {list(missing_ids)}",
        )
    
    # Get existing links to avoid duplicates
    existing_links_statement = select(WorkflowService).where(
        WorkflowService.service_id == service_id,
        WorkflowService.workflow_id.in_(request.workflow_ids),
    )
    existing_links = session.exec(existing_links_statement).all()
    existing_workflow_ids_linked = {link.workflow_id for link in existing_links}
    
    # Create new links
    new_links = []
    for workflow_id in request.workflow_ids:
        if workflow_id not in existing_workflow_ids_linked:
            new_links.append(WorkflowService(workflow_id=workflow_id, service_id=service_id))
    
    if new_links:
        session.add_all(new_links)
        session.commit()
    
    # Return all linked workflow IDs
    all_links_statement = select(WorkflowService).where(WorkflowService.service_id == service_id)
    all_links = session.exec(all_links_statement).all()
    
    return LinkResponse(linked=[link.workflow_id for link in all_links])


@router.delete("/{service_id}/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_service_from_workflow(
    service_id: int,
    workflow_id: int,
    session: Session = Depends(get_db_session),
    caller: CallerContext = Depends(get_caller),
):
    statement = select(WorkflowService).where(
        WorkflowService.service_id == service_id,
        WorkflowService.workflow_id == workflow_id,
    )
    link = session.exec(statement).first()
    
    if link:
        session.delete(link)
        session.commit()


# Exposure helper endpoint
class ExposureItem(BaseModel):
    id: int
    name: str

class ExposureResponse(BaseModel):
    experts: List[ExposureItem]
    workflows: List[ExposureItem]
    counts: dict


@router.get("/{service_id}/exposure", response_model=ExposureResponse)
def get_service_exposure(
    service_id: int,
    session: Session = Depends(get_db_session),
    caller: CallerContext = Depends(get_caller),
):
    service = session.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )
    
    # Get linked experts
    expert_statement = (
        select(Expert)
        .join(ExpertService)
        .where(ExpertService.service_id == service_id)
        .order_by(Expert.name)
    )
    experts = session.exec(expert_statement).all()
    
    # Get linked workflows
    workflow_statement = (
        select(Workflow)
        .join(WorkflowService)
        .where(WorkflowService.service_id == service_id)
        .order_by(Workflow.name)
    )
    workflows = session.exec(workflow_statement).all()
    
    return ExposureResponse(
        experts=[ExposureItem(id=expert.id, name=expert.name) for expert in experts],
        workflows=[ExposureItem(id=workflow.id, name=workflow.name) for workflow in workflows],
        counts={
            "experts": len(experts),
            "workflows": len(workflows),
        }
    )


# Whoami endpoint for API key debugging
@router.get("/whoami")
def whoami(caller: CallerContext = Depends(get_caller)):
    if caller.service:
        # Get service segments
        from app.api.deps import get_db_session
        session = next(get_db_session())
        statement = select(ServiceSegment).where(ServiceSegment.service_id == caller.service.id)
        segments = session.exec(statement).all()
        
        return {
            "service_id": caller.service.id,
            "name": caller.service.name,
            "environment": caller.service.environment,
            "segments": [{"id": seg.id, "name": seg.name} for seg in segments],
        }
    elif caller.user:
        return {
            "user_id": caller.user.id,
            "email": getattr(caller.user, "email", "N/A"),
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid authentication found",
        ) 