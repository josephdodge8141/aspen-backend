import json
import asyncio
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from app.services.runs.registry import REGISTRY


router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


@router.get("/runs/{run_id}/events")
async def stream_run_events(run_id: str):
    """Stream run events via Server-Sent Events (SSE)."""
    
    async def event_generator():
        # First, send any existing events from the backlog
        run_state = REGISTRY.get(run_id)
        if run_state is None:
            yield {
                "event": "error",
                "data": json.dumps({"error": "Run not found"})
            }
            return
        
        # Send backlog events
        for event in run_state.events:
            yield {
                "event": "log",
                "data": json.dumps({
                    "ts": event.ts,
                    "level": event.level,
                    "message": event.message,
                    "data": event.data
                })
            }
        
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
                    "data": json.dumps({
                        "ts": event.ts,
                        "level": event.level,
                        "message": event.message,
                        "data": event.data
                    })
                }
            else:
                # Timeout - send heartbeat
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({"ts": asyncio.get_event_loop().time()})
                }
            
            # Check if run is finished after processing event
            current_state = REGISTRY.get(run_id)
            if current_state and current_state.finished_at is not None:
                yield {
                    "event": "done",
                    "data": json.dumps({"finished_at": current_state.finished_at})
                }
                break
    
    return EventSourceResponse(event_generator()) 