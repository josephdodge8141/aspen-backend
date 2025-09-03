import time
from typing import Any
from .registry import REGISTRY, RunEvent


def log_info(run_id: str, msg: str, **data) -> None:
    event = RunEvent(ts=time.time(), level="info", message=msg, data=data)
    REGISTRY.append(run_id, event)


def log_warn(run_id: str, msg: str, **data) -> None:
    event = RunEvent(ts=time.time(), level="warn", message=msg, data=data)
    REGISTRY.append(run_id, event)


def log_error(run_id: str, msg: str, exception: Exception = None, **data) -> None:
    if exception is not None:
        data["exception"] = {
            "type": type(exception).__name__,
            "message": str(exception),
        }

    event = RunEvent(ts=time.time(), level="error", message=msg, data=data)
    REGISTRY.append(run_id, event)


def finish(run_id: str) -> None:
    REGISTRY.finish(run_id)
