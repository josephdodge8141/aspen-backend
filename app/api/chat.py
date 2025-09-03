import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_db_session, get_caller, CallerContext
from app.models.experts import Expert
from app.models.workflows import Workflow
from app.security.permissions import require_team_member
from app.security.guardrails import (
    ensure_service_can_use_expert,
    ensure_service_can_use_workflow,
)
from app.services.dag_validate import validate_dag
from app.services.dag_available import resolve_inputs_for_node
from app.services.nodes.base import get_service
from app.repos.workflows_repo import get_nodes_and_edges
from app.services.runs.registry import REGISTRY
from app.services.runs import logger
from app.services.prompt_render import render_prompt, get_base_defaults


router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


class RunExpertBody(BaseModel):
    expert_id: int
    input_params: dict = {}
    base: dict = {}  # optional overrides for base values


class RunExpertResponse(BaseModel):
    run_id: str
    messages: list[dict]


class RunWorkflowBody(BaseModel):
    workflow_id: int
    starting_inputs: dict = {}


class RunWorkflowResponse(BaseModel):
    run_id: str
    steps: list[dict]


@router.get("/runs/{run_id}/events")
async def stream_run_events(run_id: str):
    """Stream run events via Server-Sent Events (SSE)."""

    async def event_generator():
        # First, send any existing events from the backlog
        run_state = REGISTRY.get(run_id)
        if run_state is None:
            yield {"event": "error", "data": json.dumps({"error": "Run not found"})}
            return

        # Send backlog events
        backlog_count = len(run_state.events)
        for event in run_state.events:
            yield {
                "event": "log",
                "data": json.dumps(
                    {
                        "ts": event.ts,
                        "level": event.level,
                        "message": event.message,
                        "data": event.data,
                    }
                ),
            }

        # Clear the queue of events that were already in backlog to avoid duplication
        for _ in range(backlog_count):
            try:
                run_state.q.get_nowait()
            except:
                break

        # Stream new events until run is finished
        while True:
            # Check if run is finished
            current_state = REGISTRY.get(run_id)
            if current_state is None:
                break

            # Pop next event with timeout
            event = REGISTRY.pop_next(run_id, timeout=20.0)

            if event is not None:
                yield {
                    "event": "log",
                    "data": json.dumps(
                        {
                            "ts": event.ts,
                            "level": event.level,
                            "message": event.message,
                            "data": event.data,
                        }
                    ),
                }
            else:
                # Timeout - send heartbeat
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({"ts": asyncio.get_event_loop().time()}),
                }

            # Check if run is finished after processing event
            current_state = REGISTRY.get(run_id)
            if current_state and current_state.finished_at is not None:
                yield {
                    "event": "done",
                    "data": json.dumps({"finished_at": current_state.finished_at}),
                }
                break

    return EventSourceResponse(event_generator())


@router.post("/experts:run", response_model=RunExpertResponse)
def run_expert(
    body: RunExpertBody,
    caller: CallerContext = Depends(get_caller),
    session: Session = Depends(get_db_session),
):
    """Run an expert with input parameters and return stubbed response."""

    # Fetch the expert
    expert = session.get(Expert, body.expert_id)
    if expert is None:
        raise HTTPException(
            status_code=404,
            detail="Expert not found",
            headers={"Content-Type": "application/problem+json"},
        )

    # Check permissions
    if caller.service:
        # Service must be linked to this expert
        ensure_service_can_use_expert(session, caller.service.id, body.expert_id)
    elif caller.user:
        # User must be team member
        require_team_member(session, caller.user, expert.team_id)
    else:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"Content-Type": "application/problem+json"},
        )

    # Create run
    run_state = REGISTRY.create("expert")
    run_id = run_state.run_id

    try:
        # Prepare base values (defaults + overrides)
        base_values = get_base_defaults()
        base_values.update(body.base)

        # Render the prompt
        rendered_prompt, warnings = render_prompt(
            expert.prompt, base_values, body.input_params
        )

        # Log the start of execution
        logger.log_info(
            run_id,
            "Expert execution started",
            expert_id=expert.id,
            expert_name=expert.name,
            model_name=expert.model_name,
            input_size=len(str(body.input_params)),
            warnings=warnings,
        )

        # Log prompt rendered
        logger.log_info(
            run_id,
            "Prompt rendered",
            rendered_length=len(rendered_prompt),
            warnings_count=len(warnings),
        )

        if warnings:
            for warning in warnings:
                logger.log_warn(run_id, "Prompt rendering warning", warning=warning)

        # Create messages (user prompt + stubbed assistant response)
        messages = [
            {"role": "user", "content": rendered_prompt},
            {
                "role": "assistant",
                "content": f"(stubbed response from {expert.model_name})",
            },
        ]

        # Log assistant response
        logger.log_info(
            run_id,
            "Assistant stub sent",
            model_name=expert.model_name,
            response_type="stubbed",
        )

        # Finish the run
        logger.finish(run_id)

        return RunExpertResponse(run_id=run_id, messages=messages)

    except Exception as e:
        # Log error and finish run
        logger.log_error(
            run_id, "Expert execution failed", exception=e, expert_id=expert.id
        )
        logger.finish(run_id)
        raise


@router.post("/workflows:run", response_model=RunWorkflowResponse)
def run_workflow(
    body: RunWorkflowBody,
    caller: CallerContext = Depends(get_caller),
    session: Session = Depends(get_db_session),
):
    """Run a workflow step-by-step and return execution results."""

    # Fetch the workflow
    workflow = session.get(Workflow, body.workflow_id)
    if workflow is None:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found",
            headers={"Content-Type": "application/problem+json"},
        )

    # Check permissions
    if caller.service:
        # Service must be linked to this workflow
        ensure_service_can_use_workflow(session, caller.service.id, body.workflow_id)
    elif caller.user:
        # User must be team member
        require_team_member(session, caller.user, workflow.team_id)
    else:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"Content-Type": "application/problem+json"},
        )

    # Create run
    run_state = REGISTRY.create("workflow")
    run_id = run_state.run_id

    try:
        # Load nodes and edges
        nodes, edges = get_nodes_and_edges(session, body.workflow_id)

        # Validate DAG
        try:
            topo_order = validate_dag(nodes, edges)
        except ValueError as e:
            logger.log_error(
                run_id,
                "Workflow DAG validation failed",
                exception=e,
                workflow_id=workflow.id,
            )
            logger.finish(run_id)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid workflow DAG: {str(e)}",
                headers={"Content-Type": "application/problem+json"},
            )

        # Log workflow execution start
        logger.log_info(
            run_id,
            "Workflow execution started",
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            node_count=len(nodes),
            edge_count=len(edges),
        )

        # Execute nodes in topological order
        outputs_by_node = {}
        steps = []

        # Add starting inputs as "virtual node 0" outputs
        if body.starting_inputs:
            outputs_by_node[0] = body.starting_inputs
            logger.log_info(
                run_id, "Starting inputs provided", inputs=body.starting_inputs
            )

        for node in topo_order:
            logger.log_info(
                run_id,
                "Node execution started",
                node_id=node.id,
                node_type=node.node_type.value,
                node_metadata=node.node_metadata,
            )

            try:
                # Resolve inputs for this node
                node_inputs = resolve_inputs_for_node(node.id, outputs_by_node)

                # Get the node service and execute
                service = get_service(node.node_type)
                node_output = service.execute(node_inputs, node.node_metadata)

                # Store output for future nodes
                outputs_by_node[node.id] = node_output

                # Log successful execution
                logger.log_info(
                    run_id,
                    "Node execution completed",
                    node_id=node.id,
                    output=node_output,
                )

                # Add to steps
                steps.append(
                    {
                        "node_id": node.id,
                        "node_type": node.node_type.value,
                        "output": node_output,
                    }
                )

            except Exception as e:
                logger.log_error(
                    run_id,
                    "Node execution failed",
                    exception=e,
                    node_id=node.id,
                    node_type=node.node_type.value,
                )
                # Continue execution for now (could make this configurable)
                steps.append(
                    {
                        "node_id": node.id,
                        "node_type": node.node_type.value,
                        "output": {},
                        "error": str(e),
                    }
                )

        # Log workflow completion
        logger.log_info(
            run_id,
            "Workflow execution completed",
            workflow_id=workflow.id,
            steps_completed=len(steps),
            total_outputs=len(outputs_by_node),
        )

        # Finish the run
        logger.finish(run_id)

        return RunWorkflowResponse(run_id=run_id, steps=steps)

    except HTTPException:
        # Re-raise HTTP exceptions (like validation errors)
        raise
    except Exception as e:
        # Log unexpected errors and finish run
        logger.log_error(
            run_id, "Workflow execution failed", exception=e, workflow_id=workflow.id
        )
        logger.finish(run_id)
        raise
