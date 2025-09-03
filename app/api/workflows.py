from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select

from app.api.deps import get_db_session, get_current_user
from app.models.users import User
from app.models.workflows import Workflow, Node, NodeNode
from app.schemas.workflows import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowRead,
    WorkflowListItem,
    NodeCreate,
    NodeUpdate,
    NodeRead,
    EdgeCreate,
    EdgeRead,
)
from app.repos.workflows_repo import list_with_counts, get_expanded
from app.security.permissions import require_team_admin
from app.lib.cron import is_valid_cron
from app.services.dag_validate import validate_dag, validate_workflow_triggers
from app.services.dag_plan import plan_workflow
from app.services.dag_available import available_data_map
from app.services.nodes.base import get_service, NodeValidationError
import app.services.nodes  # Import to trigger service registration

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflows"])


@router.get("", response_model=List[WorkflowListItem])
async def list_workflows(
    team_id: int = None,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """List workflows with expert and service counts."""
    return list_with_counts(session, team_id=team_id)


@router.post("", response_model=WorkflowRead, status_code=201)
async def create_workflow(
    workflow_data: WorkflowCreate,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new workflow."""
    # Check team admin permission
    require_team_admin(current_user, workflow_data.team_id)

    # Validate cron schedule if provided
    if workflow_data.cron_schedule and not is_valid_cron(workflow_data.cron_schedule):
        raise HTTPException(status_code=400, detail="Invalid cron schedule format")

    # Create workflow
    workflow = Workflow(
        name=workflow_data.name,
        description=workflow_data.description,
        input_params=workflow_data.input_params,
        is_api=workflow_data.is_api,
        cron_schedule=workflow_data.cron_schedule,
        team_id=workflow_data.team_id,
    )

    session.add(workflow)
    session.commit()
    session.refresh(workflow)

    return WorkflowRead(
        id=workflow.id,
        uuid=workflow.uuid,
        name=workflow.name,
        description=workflow.description,
        input_params=workflow.input_params,
        is_api=workflow.is_api,
        cron_schedule=workflow.cron_schedule,
        team_id=workflow.team_id,
    )


@router.get("/{workflow_id}", response_model=Dict[str, Any])
async def get_workflow_expanded(
    workflow_id: int,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Get workflow with expanded nodes, edges, experts, and services."""
    result = get_expanded(session, workflow_id)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return result


@router.patch("/{workflow_id}", response_model=WorkflowRead)
async def update_workflow(
    workflow_id: int,
    workflow_data: WorkflowUpdate,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Update a workflow."""
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check team admin permission
    require_team_admin(current_user, workflow.team_id)

    # Validate cron schedule if provided
    if workflow_data.cron_schedule and not is_valid_cron(workflow_data.cron_schedule):
        raise HTTPException(status_code=400, detail="Invalid cron schedule format")

    # Update fields
    update_data = workflow_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workflow, field, value)

    session.add(workflow)
    session.commit()
    session.refresh(workflow)

    return WorkflowRead(
        id=workflow.id,
        uuid=workflow.uuid,
        name=workflow.name,
        description=workflow.description,
        input_params=workflow.input_params,
        is_api=workflow.is_api,
        cron_schedule=workflow.cron_schedule,
        team_id=workflow.team_id,
    )


@router.post("/{workflow_id}:archive", response_model=WorkflowRead)
async def archive_workflow(
    workflow_id: int,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Archive a workflow (soft delete for now)."""
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check team admin permission
    require_team_admin(current_user, workflow.team_id)

    # For now, we'll just keep the record (UI will hide by convention)
    # In the future, we might add an 'archived' status field

    return WorkflowRead(
        id=workflow.id,
        uuid=workflow.uuid,
        name=workflow.name,
        description=workflow.description,
        input_params=workflow.input_params,
        is_api=workflow.is_api,
        cron_schedule=workflow.cron_schedule,
        team_id=workflow.team_id,
    )


# Node CRUD endpoints
@router.post("/{workflow_id}/nodes", response_model=NodeRead, status_code=201)
async def create_node(
    workflow_id: int,
    node_data: NodeCreate,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new node in a workflow."""
    # Check if workflow exists and get team_id for permission check
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check team admin permission
    require_team_admin(current_user, workflow.team_id)

    # Validate node metadata and structured output
    try:
        service = get_service(node_data.node_type)
        service.validate(node_data.node_metadata, node_data.structured_output)
    except NodeValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Node service error: {str(e)}")

    # Create node
    node = Node(
        workflow_id=workflow_id,
        node_type=node_data.node_type,
        node_metadata=node_data.node_metadata,
        structured_output=node_data.structured_output,
    )

    session.add(node)
    session.commit()
    session.refresh(node)

    return NodeRead(
        id=node.id,
        node_type=node.node_type,
        node_metadata=node.node_metadata,
        structured_output=node.structured_output,
    )


@router.patch("/{workflow_id}/nodes/{node_id}", response_model=NodeRead)
async def update_node(
    workflow_id: int,
    node_id: int,
    node_data: NodeUpdate,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Update a node in a workflow."""
    # Check if workflow exists and get team_id for permission check
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check team admin permission
    require_team_admin(current_user, workflow.team_id)

    # Get the node and verify it belongs to the workflow
    node = session.get(Node, node_id)
    if not node or node.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Node not found")

    # Update fields first to get the complete metadata for validation
    update_data = node_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(node, field, value)

    # Validate the updated node metadata and structured output
    try:
        service = get_service(node.node_type)
        service.validate(node.node_metadata, node.structured_output)
    except NodeValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Node service error: {str(e)}")

    session.add(node)
    session.commit()
    session.refresh(node)

    return NodeRead(
        id=node.id,
        node_type=node.node_type,
        node_metadata=node.node_metadata,
        structured_output=node.structured_output,
    )


@router.delete("/{workflow_id}/nodes/{node_id}", status_code=204)
async def delete_node(
    workflow_id: int,
    node_id: int,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a node from a workflow. Also deletes incident edges."""
    # Check if workflow exists and get team_id for permission check
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check team admin permission
    require_team_admin(current_user, workflow.team_id)

    # Get the node and verify it belongs to the workflow
    node = session.get(Node, node_id)
    if not node or node.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Node not found")

    # Delete the node (FK cascade will handle edges)
    session.delete(node)
    session.commit()

    return Response(status_code=204)


# Edge CRUD endpoints
@router.post("/{workflow_id}/edges", response_model=EdgeRead, status_code=201)
async def create_edge(
    workflow_id: int,
    edge_data: EdgeCreate,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new edge in a workflow."""
    # Check if workflow exists and get team_id for permission check
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check team admin permission
    require_team_admin(current_user, workflow.team_id)

    # Verify both nodes belong to the workflow
    parent_node = session.get(Node, edge_data.parent_id)
    child_node = session.get(Node, edge_data.child_id)

    if not parent_node or parent_node.workflow_id != workflow_id:
        raise HTTPException(status_code=400, detail="Parent node not found in workflow")

    if not child_node or child_node.workflow_id != workflow_id:
        raise HTTPException(status_code=400, detail="Child node not found in workflow")

    # Reject self-edge
    if edge_data.parent_id == edge_data.child_id:
        raise HTTPException(status_code=400, detail="Self-edges are not allowed")

    # Create edge (unique constraint will handle duplicates)
    edge = NodeNode(
        parent_id=edge_data.parent_id,
        child_id=edge_data.child_id,
        branch_label=edge_data.branch_label,
    )

    try:
        session.add(edge)
        session.commit()
        session.refresh(edge)
    except Exception as e:
        session.rollback()
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Edge already exists")
        raise HTTPException(status_code=500, detail="Failed to create edge")

    return EdgeRead(
        id=edge.id,
        parent_id=edge.parent_id,
        child_id=edge.child_id,
        branch_label=edge.branch_label,
    )


@router.delete("/{workflow_id}/edges/{edge_id}", status_code=204)
async def delete_edge(
    workflow_id: int,
    edge_id: int,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Delete an edge from a workflow."""
    # Check if workflow exists and get team_id for permission check
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check team admin permission
    require_team_admin(current_user, workflow.team_id)

    # Get the edge and verify it belongs to the workflow
    edge = session.get(NodeNode, edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")

    # Verify the edge belongs to nodes in this workflow
    parent_node = session.get(Node, edge.parent_id)
    if not parent_node or parent_node.workflow_id != workflow_id:
        raise HTTPException(status_code=404, detail="Edge not found")

    # Delete the edge
    session.delete(edge)
    session.commit()

    return Response(status_code=204)


@router.post("/{workflow_id}:validate")
async def validate_workflow(
    workflow_id: int,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Validate workflow DAG and triggers."""
    # Get workflow and verify access
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Get nodes and edges for this workflow
    nodes = session.exec(select(Node).where(Node.workflow_id == workflow_id)).all()

    edges = session.exec(
        select(NodeNode)
        .join(Node, NodeNode.parent_id == Node.id)
        .where(Node.workflow_id == workflow_id)
    ).all()

    # Validate DAG structure
    dag_result = validate_dag(list(nodes), list(edges))

    # Validate triggers
    trigger_warnings = validate_workflow_triggers(workflow)

    # Combine results
    all_warnings = dag_result.warnings + trigger_warnings

    return {
        "errors": dag_result.errors,
        "warnings": all_warnings,
        "topo_order": dag_result.topo_order,
    }


@router.post("/{workflow_id}:plan")
async def plan_workflow_execution(
    workflow_id: int,
    request_body: Dict[str, Any],
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Plan workflow execution with shape propagation."""
    # Get workflow and verify access
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Extract starting inputs from request body
    starting_inputs = request_body.get("starting_inputs", {})

    # Get nodes and edges for this workflow
    nodes = session.exec(select(Node).where(Node.workflow_id == workflow_id)).all()

    edges = session.exec(
        select(NodeNode)
        .join(Node, NodeNode.parent_id == Node.id)
        .where(Node.workflow_id == workflow_id)
    ).all()

    # Plan the workflow
    planned_steps = plan_workflow(
        list(nodes), list(edges), starting_inputs=starting_inputs
    )

    return {"steps": [step.model_dump() for step in planned_steps]}


@router.get("/{workflow_id}/available-data")
async def get_available_data(
    workflow_id: int,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Get available data for each node in the workflow."""
    # Get workflow and verify access
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Get nodes and edges for this workflow
    nodes = session.exec(select(Node).where(Node.workflow_id == workflow_id)).all()

    edges = session.exec(
        select(NodeNode)
        .join(Node, NodeNode.parent_id == Node.id)
        .where(Node.workflow_id == workflow_id)
    ).all()

    # Compute available data map
    available_data = available_data_map(list(nodes), list(edges))

    return {
        "by_node_id": {str(node_id): data for node_id, data in available_data.items()}
    }
