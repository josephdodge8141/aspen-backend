from typing import Optional, List
from sqlmodel import Session, select, func
from sqlalchemy import and_
from app.models.experts import Expert, ExpertService, ExpertWorkflow
from app.models.workflows import Workflow
from app.models.services import Service
from app.models.common import ExpertStatus
from app.schemas.experts import ExpertListItem, ExpertCreate, ExpertUpdate


class ExpertsRepo:
    def create(self, session: Session, expert: Expert) -> Expert:
        session.add(expert)
        session.commit()
        session.refresh(expert)
        return expert

    def get(self, session: Session, expert_id: int) -> Optional[Expert]:
        return session.get(Expert, expert_id)

    def get_by_uuid(self, session: Session, uuid: str) -> Optional[Expert]:
        statement = select(Expert).where(Expert.uuid == uuid)
        return session.exec(statement).first()

    def list(
        self,
        session: Session,
        *,
        team_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[Expert]:
        statement = select(Expert)
        if team_id is not None:
            statement = statement.where(Expert.team_id == team_id)
        if status is not None:
            statement = statement.where(Expert.status == status)
        return session.exec(statement).all()

    def update(self, session: Session, expert: Expert) -> Expert:
        session.add(expert)
        session.commit()
        session.refresh(expert)
        return expert

    def delete(self, session: Session, expert_id: int) -> bool:
        expert = session.get(Expert, expert_id)
        if expert:
            session.delete(expert)
            session.commit()
            return True
        return False

    def add_service(
        self, session: Session, expert_id: int, service_id: int
    ) -> ExpertService:
        expert_service = ExpertService(expert_id=expert_id, service_id=service_id)
        session.add(expert_service)
        session.commit()
        session.refresh(expert_service)
        return expert_service

    def remove_service(self, session: Session, expert_id: int, service_id: int) -> bool:
        statement = select(ExpertService).where(
            ExpertService.expert_id == expert_id, ExpertService.service_id == service_id
        )
        expert_service = session.exec(statement).first()
        if expert_service:
            session.delete(expert_service)
            session.commit()
            return True
        return False

    def add_workflow(
        self, session: Session, expert_id: int, workflow_id: int
    ) -> ExpertWorkflow:
        expert_workflow = ExpertWorkflow(expert_id=expert_id, workflow_id=workflow_id)
        session.add(expert_workflow)
        session.commit()
        session.refresh(expert_workflow)
        return expert_workflow

    def remove_workflow(
        self, session: Session, expert_id: int, workflow_id: int
    ) -> bool:
        statement = select(ExpertWorkflow).where(
            ExpertWorkflow.expert_id == expert_id,
            ExpertWorkflow.workflow_id == workflow_id,
        )
        expert_workflow = session.exec(statement).first()
        if expert_workflow:
            session.delete(expert_workflow)
            session.commit()
            return True
        return False

    def list_with_counts(
        self,
        session: Session,
        *,
        team_id: Optional[int] = None,
        status: Optional[List[ExpertStatus]] = None,
    ) -> List[ExpertListItem]:
        # Build the base query with JOINs and aggregates
        workflow_count = (
            select(func.count(ExpertWorkflow.workflow_id))
            .where(ExpertWorkflow.expert_id == Expert.id)
            .scalar_subquery()
        )

        service_count = (
            select(func.count(ExpertService.service_id))
            .where(ExpertService.expert_id == Expert.id)
            .scalar_subquery()
        )

        statement = select(
            Expert,
            workflow_count.label("workflows_count"),
            service_count.label("services_count"),
        )

        # Apply filters
        if team_id is not None:
            statement = statement.where(Expert.team_id == team_id)

        if status is not None:
            statement = statement.where(Expert.status.in_(status))

        # Execute query and build result
        results = session.exec(statement).all()

        list_items = []
        for expert, workflows_count, services_count in results:
            # Truncate prompt to 120 chars with ellipsis
            prompt_truncated = expert.prompt
            if len(prompt_truncated) > 120:
                prompt_truncated = prompt_truncated[:120] + "…"

            list_items.append(
                ExpertListItem(
                    id=expert.id,
                    name=expert.name,
                    model_name=expert.model_name,
                    status=expert.status,
                    prompt_truncated=prompt_truncated,
                    workflows_count=workflows_count or 0,
                    services_count=services_count or 0,
                    team_id=expert.team_id,
                )
            )

        return list_items

    def get_with_expanded(self, session: Session, expert_id: int) -> Optional[dict]:
        # Get the expert
        expert = session.get(Expert, expert_id)
        if not expert:
            return None

        # Get linked workflows with names
        workflow_stmt = (
            select(Workflow.id, Workflow.name)
            .join(ExpertWorkflow, ExpertWorkflow.workflow_id == Workflow.id)
            .where(ExpertWorkflow.expert_id == expert_id)
        )
        workflows = [
            {"id": wf_id, "name": wf_name}
            for wf_id, wf_name in session.exec(workflow_stmt).all()
        ]

        # Get linked services with names and environment
        service_stmt = (
            select(Service.id, Service.name, Service.environment)
            .join(ExpertService, ExpertService.service_id == Service.id)
            .where(ExpertService.expert_id == expert_id)
        )
        services = [
            {"id": svc_id, "name": svc_name, "environment": svc_env.value}
            for svc_id, svc_name, svc_env in session.exec(service_stmt).all()
        ]

        return {
            "expert": {
                "id": expert.id,
                "uuid": expert.uuid,
                "name": expert.name,
                "prompt": expert.prompt,
                "model_name": expert.model_name,
                "status": expert.status,
                "input_params": expert.input_params,
                "team_id": expert.team_id,
            },
            "workflows": workflows,
            "services": services,
        }


# Standalone CRUD functions for API endpoints
def create_expert(session: Session, expert_data: ExpertCreate) -> Expert:
    """Create a new expert from ExpertCreate schema."""
    expert = Expert(
        name=expert_data.name,
        prompt=expert_data.prompt,
        input_params=expert_data.input_params,
        team_id=expert_data.team_id,
        status=expert_data.status,
        model_name=expert_data.model_name,
    )
    session.add(expert)
    session.commit()
    session.refresh(expert)
    return expert


def get_expert(session: Session, expert_id: int) -> Optional[Expert]:
    """Get an expert by ID."""
    return session.get(Expert, expert_id)


def update_expert(
    session: Session, expert_id: int, expert_data: ExpertUpdate
) -> Expert:
    """Update an expert with partial data from ExpertUpdate schema."""
    expert = session.get(Expert, expert_id)
    if not expert:
        raise ValueError(f"Expert with id {expert_id} not found")

    # Update only the provided fields
    update_data = expert_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(expert, field, value)

    session.add(expert)
    session.commit()
    session.refresh(expert)
    return expert


def list_with_counts(
    session: Session,
    *,
    team_id: Optional[int] = None,
    status: Optional[List[ExpertStatus]] = None,
) -> List[ExpertListItem]:
    """List experts with workflow and service counts. Standalone version for API."""
    # Build the base query with JOINs and aggregates
    workflow_count = (
        select(func.count(ExpertWorkflow.workflow_id))
        .where(ExpertWorkflow.expert_id == Expert.id)
        .scalar_subquery()
    )

    service_count = (
        select(func.count(ExpertService.service_id))
        .where(ExpertService.expert_id == Expert.id)
        .scalar_subquery()
    )

    statement = select(
        Expert,
        workflow_count.label("workflows_count"),
        service_count.label("services_count"),
    )

    # Apply filters
    if team_id is not None:
        statement = statement.where(Expert.team_id == team_id)

    if status is not None:
        statement = statement.where(Expert.status.in_(status))

    # Execute query and build result
    results = session.exec(statement).all()

    list_items = []
    for expert, workflows_count, services_count in results:
        # Truncate prompt to 120 chars with ellipsis
        prompt_truncated = expert.prompt
        if len(prompt_truncated) > 120:
            prompt_truncated = prompt_truncated[:120] + "…"

        list_items.append(
            ExpertListItem(
                id=expert.id,
                name=expert.name,
                model_name=expert.model_name,
                status=expert.status,
                prompt_truncated=prompt_truncated,
                workflows_count=workflows_count or 0,
                services_count=services_count or 0,
                team_id=expert.team_id,
            )
        )

    return list_items


def get_with_expanded(session: Session, expert_id: int) -> Optional[dict]:
    """Get expert with expanded workflows and services. Standalone version for API."""
    # Get the expert
    expert = session.get(Expert, expert_id)
    if not expert:
        return None

    # Get linked workflows with names
    workflow_stmt = (
        select(Workflow.id, Workflow.name)
        .join(ExpertWorkflow, ExpertWorkflow.workflow_id == Workflow.id)
        .where(ExpertWorkflow.expert_id == expert_id)
    )
    workflows = [
        {"id": wf_id, "name": wf_name}
        for wf_id, wf_name in session.exec(workflow_stmt).all()
    ]

    # Get linked services with names and environment
    service_stmt = (
        select(Service.id, Service.name, Service.environment)
        .join(ExpertService, ExpertService.service_id == Service.id)
        .where(ExpertService.expert_id == expert_id)
    )
    services = [
        {"id": svc_id, "name": svc_name, "environment": svc_env.value}
        for svc_id, svc_name, svc_env in session.exec(service_stmt).all()
    ]

    return {
        "id": expert.id,
        "uuid": expert.uuid,
        "name": expert.name,
        "prompt": expert.prompt,
        "model_name": expert.model_name,
        "status": expert.status.value,
        "input_params": expert.input_params,
        "team_id": expert.team_id,
        "workflows": workflows,
        "services": services,
    }

# Standalone functions for workflow link management
def add_expert_workflow_links(session: Session, expert_id: int, workflow_ids: list[int]) -> dict:
    """Add workflow links to an expert. Returns updated expanded view."""
    from app.models.workflows import Workflow
    
    # Validate expert exists
    expert = session.get(Expert, expert_id)
    if not expert:
        raise ValueError(f"Expert with id {expert_id} not found")
    
    # Validate all workflows exist
    for workflow_id in workflow_ids:
        workflow = session.get(Workflow, workflow_id)
        if not workflow:
            raise ValueError(f"Workflow with id {workflow_id} not found")
    
    # Add links (ignore duplicates)
    for workflow_id in workflow_ids:
        # Check if link already exists
        existing = session.exec(
            select(ExpertWorkflow).where(
                ExpertWorkflow.expert_id == expert_id,
                ExpertWorkflow.workflow_id == workflow_id
            )
        ).first()
        
        if not existing:
            expert_workflow = ExpertWorkflow(expert_id=expert_id, workflow_id=workflow_id)
            session.add(expert_workflow)
    
    session.commit()
    
    # Return updated expanded view
    return get_with_expanded(session, expert_id)


def remove_expert_workflow_link(session: Session, expert_id: int, workflow_id: int) -> bool:
    """Remove a workflow link from an expert. Returns True if removed, False if not found."""
    # Validate expert exists
    expert = session.get(Expert, expert_id)
    if not expert:
        raise ValueError(f"Expert with id {expert_id} not found")
    
    # Find and remove the link
    statement = select(ExpertWorkflow).where(
        ExpertWorkflow.expert_id == expert_id,
        ExpertWorkflow.workflow_id == workflow_id,
    )
    expert_workflow = session.exec(statement).first()
    if expert_workflow:
        session.delete(expert_workflow)
        session.commit()
        return True
    return False


# Standalone functions for service link management
def add_expert_service_links(session: Session, expert_id: int, service_ids: list[int]) -> dict:
    """Add service links to an expert. Returns updated expanded view."""
    from app.models.services import Service
    
    # Validate expert exists
    expert = session.get(Expert, expert_id)
    if not expert:
        raise ValueError(f"Expert with id {expert_id} not found")
    
    # Validate all services exist
    for service_id in service_ids:
        service = session.get(Service, service_id)
        if not service:
            raise ValueError(f"Service with id {service_id} not found")
    
    # Add links (ignore duplicates)
    for service_id in service_ids:
        # Check if link already exists
        existing = session.exec(
            select(ExpertService).where(
                ExpertService.expert_id == expert_id,
                ExpertService.service_id == service_id
            )
        ).first()
        
        if not existing:
            expert_service = ExpertService(expert_id=expert_id, service_id=service_id)
            session.add(expert_service)
    
    session.commit()
    
    # Return updated expanded view
    return get_with_expanded(session, expert_id)


def remove_expert_service_link(session: Session, expert_id: int, service_id: int) -> bool:
    """Remove a service link from an expert. Returns True if removed, False if not found."""
    # Validate expert exists
    expert = session.get(Expert, expert_id)
    if not expert:
        raise ValueError(f"Expert with id {expert_id} not found")
    
    # Find and remove the link
    statement = select(ExpertService).where(
        ExpertService.expert_id == expert_id,
        ExpertService.service_id == service_id,
    )
    expert_service = session.exec(statement).first()
    if expert_service:
        session.delete(expert_service)
        session.commit()
        return True
    return False
