from typing import Optional, List, Dict, Any
from sqlmodel import Session, select, func
from sqlalchemy import and_

from app.models.workflows import Workflow, Node, NodeNode
from app.models.experts import Expert, ExpertWorkflow, ExpertService
from app.models.services import Service
from app.schemas.workflows import WorkflowListItem, WorkflowRead, NodeRead, EdgeRead


def truncate_description(
    description: Optional[str], max_length: int = 120
) -> Optional[str]:
    """Truncate description to max_length characters with ellipsis if needed."""
    if not description:
        return description
    if len(description) <= max_length:
        return description
    return description[:max_length] + "..."


def list_with_counts(
    session: Session, *, team_id: Optional[int] = None
) -> List[WorkflowListItem]:
    """List workflows with expert and service counts, plus first 5 expert names."""

    # Build the base query with aggregates for counts
    experts_count_subquery = (
        select(func.count(ExpertWorkflow.expert_id))
        .where(ExpertWorkflow.workflow_id == Workflow.id)
        .scalar_subquery()
    )

    services_count_subquery = (
        select(func.count(ExpertService.service_id.distinct()))
        .select_from(ExpertService)
        .join(ExpertWorkflow, ExpertService.expert_id == ExpertWorkflow.expert_id)
        .where(ExpertWorkflow.workflow_id == Workflow.id)
        .scalar_subquery()
    )

    statement = select(
        Workflow,
        experts_count_subquery.label("experts_count"),
        services_count_subquery.label("services_count"),
    )

    # Apply team filter if provided
    if team_id is not None:
        statement = statement.where(Workflow.team_id == team_id)

    # Order by name for stable results
    statement = statement.order_by(Workflow.name)

    # Execute main query
    results = session.exec(statement).all()

    # For each workflow, get the first 5 expert names
    list_items = []
    for workflow, experts_count, services_count in results:
        # Get first 5 experts for this workflow
        experts_query = (
            select(Expert.id, Expert.name)
            .join(ExpertWorkflow, Expert.id == ExpertWorkflow.expert_id)
            .where(ExpertWorkflow.workflow_id == workflow.id)
            .order_by(Expert.name)
            .limit(5)
        )
        expert_results = session.exec(experts_query).all()

        experts_list = [
            {"id": expert_id, "name": expert_name}
            for expert_id, expert_name in expert_results
        ]

        list_items.append(
            WorkflowListItem(
                id=workflow.id,
                uuid=workflow.uuid,
                name=workflow.name,
                description_truncated=truncate_description(workflow.description),
                experts=experts_list,
                experts_count=experts_count or 0,
                services_count=services_count or 0,
            )
        )

    return list_items


def get_expanded(session: Session, workflow_id: int) -> Optional[Dict[str, Any]]:
    """Get workflow with expanded nodes, edges, experts, and services."""

    # Get the workflow
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        return None

    # Get nodes for this workflow
    nodes_query = select(Node).where(Node.workflow_id == workflow_id).order_by(Node.id)
    nodes = session.exec(nodes_query).all()

    # Get edges for this workflow
    edges_query = (
        select(NodeNode)
        .join(Node, NodeNode.parent_id == Node.id)
        .where(Node.workflow_id == workflow_id)
        .order_by(NodeNode.id)
    )
    edges = session.exec(edges_query).all()

    # Get experts linked to this workflow
    experts_query = (
        select(Expert.id, Expert.name)
        .join(ExpertWorkflow, Expert.id == ExpertWorkflow.expert_id)
        .where(ExpertWorkflow.workflow_id == workflow_id)
        .order_by(Expert.name)
    )
    expert_results = session.exec(experts_query).all()
    experts_list = [
        {"id": expert_id, "name": expert_name}
        for expert_id, expert_name in expert_results
    ]

    # Get services linked to this workflow (through experts)
    services_query = (
        select(Service.id, Service.name, Service.environment)
        .join(ExpertService, Service.id == ExpertService.service_id)
        .join(ExpertWorkflow, ExpertService.expert_id == ExpertWorkflow.expert_id)
        .where(ExpertWorkflow.workflow_id == workflow_id)
        .distinct()
        .order_by(Service.name, Service.environment)
    )
    service_results = session.exec(services_query).all()
    services_list = [
        {"id": service_id, "name": service_name, "environment": environment.value}
        for service_id, service_name, environment in service_results
    ]

    return {
        "workflow": WorkflowRead(
            id=workflow.id,
            uuid=workflow.uuid,
            name=workflow.name,
            description=workflow.description,
            input_params=workflow.input_params,
            is_api=workflow.is_api,
            cron_schedule=workflow.cron_schedule,
            team_id=workflow.team_id,
        ),
        "nodes": [
            NodeRead(
                id=node.id,
                node_type=node.node_type,
                node_metadata=node.node_metadata,
                structured_output=node.structured_output,
            )
            for node in nodes
        ],
        "edges": [
            EdgeRead(
                id=edge.id,
                parent_id=edge.parent_id,
                child_id=edge.child_id,
                branch_label=edge.branch_label,
            )
            for edge in edges
        ],
        "experts": experts_list,
        "services": services_list,
    }
