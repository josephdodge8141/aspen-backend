import time
import queue
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunEvent:
    ts: float
    level: str  # "info" | "warn" | "error"
    message: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunState:
    run_id: str
    kind: str  # "expert" | "workflow"
    started_at: float
    finished_at: float | None = None
    events: list[RunEvent] = field(default_factory=list)
    q: "queue.Queue[RunEvent]" = field(default_factory=queue.Queue)


class RunRegistry:
    def __init__(self, ttl_seconds: int = 900):
        self.ttl_seconds = ttl_seconds
        self.runs: dict[str, RunState] = {}
        self.lock = threading.RLock()
        self._gc_thread = None
        self._stop_gc = threading.Event()
        self._start_gc_thread()

    def _start_gc_thread(self):
        if self._gc_thread is None or not self._gc_thread.is_alive():
            self._gc_thread = threading.Thread(target=self._gc_loop, daemon=True)
            self._gc_thread.start()

    def _gc_loop(self):
        while not self._stop_gc.wait(60):  # Check every minute
            self.gc()

    def create(self, kind: str) -> RunState:
        run_id = str(uuid.uuid4())
        run_state = RunState(run_id=run_id, kind=kind, started_at=time.time())

        with self.lock:
            self.runs[run_id] = run_state

        return run_state

    def get(self, run_id: str) -> RunState | None:
        with self.lock:
            return self.runs.get(run_id)

    def append(self, run_id: str, event: RunEvent) -> None:
        with self.lock:
            run_state = self.runs.get(run_id)
            if run_state is None:
                return

            run_state.events.append(event)
            try:
                run_state.q.put_nowait(event)
            except queue.Full:
                pass  # Drop event if queue is full

    def finish(self, run_id: str) -> None:
        with self.lock:
            run_state = self.runs.get(run_id)
            if run_state is None:
                return

            run_state.finished_at = time.time()

    def pop_next(self, run_id: str, timeout: float = 20.0) -> RunEvent | None:
        with self.lock:
            run_state = self.runs.get(run_id)
            if run_state is None:
                return None

        try:
            return run_state.q.get(timeout=timeout)
        except queue.Empty:
            return None

    def gc(self) -> None:
        current_time = time.time()
        to_remove = []

        with self.lock:
            for run_id, run_state in self.runs.items():
                # Remove if finished and past TTL, or if started more than 2*TTL ago (stuck runs)
                if run_state.finished_at is not None:
                    if current_time - run_state.finished_at > self.ttl_seconds:
                        to_remove.append(run_id)
                elif current_time - run_state.started_at > (self.ttl_seconds * 2):
                    to_remove.append(run_id)

            for run_id in to_remove:
                del self.runs[run_id]

    def stop(self):
        self._stop_gc.set()
        if self._gc_thread and self._gc_thread.is_alive():
            self._gc_thread.join(timeout=1.0)


REGISTRY = RunRegistry()
