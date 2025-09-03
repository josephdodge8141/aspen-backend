import time
import threading
import pytest
from app.services.runs.registry import RunRegistry, RunEvent, RunState, REGISTRY
from app.services.runs import logger


class TestRunRegistry:
    def setup_method(self):
        self.registry = RunRegistry(ttl_seconds=2)  # Short TTL for testing

    def teardown_method(self):
        self.registry.stop()

    def test_create_run(self):
        run_state = self.registry.create("expert")

        assert run_state.run_id is not None
        assert run_state.kind == "expert"
        assert run_state.started_at > 0
        assert run_state.finished_at is None
        assert len(run_state.events) == 0

    def test_get_run(self):
        run_state = self.registry.create("workflow")

        retrieved = self.registry.get(run_state.run_id)
        assert retrieved is not None
        assert retrieved.run_id == run_state.run_id
        assert retrieved.kind == "workflow"

    def test_get_nonexistent_run(self):
        result = self.registry.get("nonexistent-id")
        assert result is None

    def test_append_event(self):
        run_state = self.registry.create("expert")
        event = RunEvent(
            ts=time.time(), level="info", message="Test message", data={"key": "value"}
        )

        self.registry.append(run_state.run_id, event)

        retrieved = self.registry.get(run_state.run_id)
        assert len(retrieved.events) == 1
        assert retrieved.events[0].message == "Test message"
        assert retrieved.events[0].data["key"] == "value"

    def test_append_to_nonexistent_run(self):
        event = RunEvent(ts=time.time(), level="info", message="Test")
        # Should not raise an error
        self.registry.append("nonexistent-id", event)

    def test_finish_run(self):
        run_state = self.registry.create("expert")
        assert run_state.finished_at is None

        self.registry.finish(run_state.run_id)

        retrieved = self.registry.get(run_state.run_id)
        assert retrieved.finished_at is not None
        assert retrieved.finished_at > run_state.started_at

    def test_finish_nonexistent_run(self):
        # Should not raise an error
        self.registry.finish("nonexistent-id")

    def test_pop_next_event(self):
        run_state = self.registry.create("expert")
        event = RunEvent(ts=time.time(), level="info", message="Test message")

        self.registry.append(run_state.run_id, event)

        popped = self.registry.pop_next(run_state.run_id, timeout=0.1)
        assert popped is not None
        assert popped.message == "Test message"

    def test_pop_next_timeout(self):
        run_state = self.registry.create("expert")

        # No events, should timeout
        popped = self.registry.pop_next(run_state.run_id, timeout=0.1)
        assert popped is None

    def test_pop_next_nonexistent_run(self):
        result = self.registry.pop_next("nonexistent-id", timeout=0.1)
        assert result is None

    def test_gc_removes_finished_runs(self):
        # Create and finish a run
        run_state = self.registry.create("expert")
        self.registry.finish(run_state.run_id)

        # Wait for TTL to expire
        time.sleep(2.1)

        # Manually trigger GC
        self.registry.gc()

        # Run should be removed
        assert self.registry.get(run_state.run_id) is None

    def test_gc_removes_stuck_runs(self):
        # Create a run but don't finish it
        run_state = self.registry.create("expert")

        # Manually set started_at to past 2*TTL
        run_state.started_at = time.time() - (self.registry.ttl_seconds * 2 + 1)

        # Manually trigger GC
        self.registry.gc()

        # Run should be removed
        assert self.registry.get(run_state.run_id) is None

    def test_gc_keeps_active_runs(self):
        # Create a recent run
        run_state = self.registry.create("expert")

        # GC should not remove it
        self.registry.gc()

        assert self.registry.get(run_state.run_id) is not None

    def test_concurrent_operations(self):
        """Test thread safety with concurrent producers and consumers."""
        run_state = self.registry.create("expert")
        events_sent = []
        events_received = []

        def producer():
            for i in range(10):
                event = RunEvent(
                    ts=time.time(),
                    level="info",
                    message=f"Message {i}",
                    data={"index": i},
                )
                events_sent.append(event)
                self.registry.append(run_state.run_id, event)
                time.sleep(0.01)  # Small delay

        def consumer():
            while len(events_received) < 10:
                event = self.registry.pop_next(run_state.run_id, timeout=1.0)
                if event:
                    events_received.append(event)

        # Start producer and consumer threads
        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)

        producer_thread.start()
        consumer_thread.start()

        producer_thread.join()
        consumer_thread.join()

        # All events should be received
        assert len(events_received) == 10

        # Messages should match (order might differ due to threading)
        sent_messages = {e.message for e in events_sent}
        received_messages = {e.message for e in events_received}
        assert sent_messages == received_messages

    def test_multiple_runs_isolation(self):
        """Test that events from different runs don't interfere."""
        run1 = self.registry.create("expert")
        run2 = self.registry.create("workflow")

        event1 = RunEvent(ts=time.time(), level="info", message="Run 1 event")
        event2 = RunEvent(ts=time.time(), level="info", message="Run 2 event")

        self.registry.append(run1.run_id, event1)
        self.registry.append(run2.run_id, event2)

        # Each run should only see its own events
        popped1 = self.registry.pop_next(run1.run_id, timeout=0.1)
        popped2 = self.registry.pop_next(run2.run_id, timeout=0.1)

        assert popped1.message == "Run 1 event"
        assert popped2.message == "Run 2 event"


class TestRunEvent:
    def test_run_event_creation(self):
        event = RunEvent(
            ts=123456.789,
            level="warn",
            message="Warning message",
            data={"error_code": 404},
        )

        assert event.ts == 123456.789
        assert event.level == "warn"
        assert event.message == "Warning message"
        assert event.data["error_code"] == 404

    def test_run_event_default_data(self):
        event = RunEvent(ts=time.time(), level="info", message="Test")
        assert event.data == {}


class TestRunState:
    def test_run_state_creation(self):
        run_state = RunState(run_id="test-id", kind="expert", started_at=123456.789)

        assert run_state.run_id == "test-id"
        assert run_state.kind == "expert"
        assert run_state.started_at == 123456.789
        assert run_state.finished_at is None
        assert len(run_state.events) == 0
        assert run_state.q is not None


class TestRunLogger:
    def test_log_info(self):
        run_state = REGISTRY.create("expert")

        logger.log_info(run_state.run_id, "Test info message", key="value")

        retrieved = REGISTRY.get(run_state.run_id)
        assert len(retrieved.events) == 1
        event = retrieved.events[0]
        assert event.level == "info"
        assert event.message == "Test info message"
        assert event.data["key"] == "value"

    def test_log_warn(self):
        run_state = REGISTRY.create("expert")

        logger.log_warn(run_state.run_id, "Test warning", code=404)

        retrieved = REGISTRY.get(run_state.run_id)
        assert len(retrieved.events) == 1
        event = retrieved.events[0]
        assert event.level == "warn"
        assert event.message == "Test warning"
        assert event.data["code"] == 404

    def test_log_error_without_exception(self):
        run_state = REGISTRY.create("expert")

        logger.log_error(run_state.run_id, "Test error", error_code="E001")

        retrieved = REGISTRY.get(run_state.run_id)
        assert len(retrieved.events) == 1
        event = retrieved.events[0]
        assert event.level == "error"
        assert event.message == "Test error"
        assert event.data["error_code"] == "E001"
        assert "exception" not in event.data

    def test_log_error_with_exception(self):
        run_state = REGISTRY.create("expert")

        try:
            raise ValueError("Something went wrong")
        except ValueError as e:
            logger.log_error(
                run_state.run_id,
                "Test error with exception",
                exception=e,
                context="test",
            )

        retrieved = REGISTRY.get(run_state.run_id)
        assert len(retrieved.events) == 1
        event = retrieved.events[0]
        assert event.level == "error"
        assert event.message == "Test error with exception"
        assert event.data["context"] == "test"
        assert event.data["exception"]["type"] == "ValueError"
        assert event.data["exception"]["message"] == "Something went wrong"

    def test_finish_run(self):
        run_state = REGISTRY.create("expert")
        assert run_state.finished_at is None

        logger.finish(run_state.run_id)

        retrieved = REGISTRY.get(run_state.run_id)
        assert retrieved.finished_at is not None

    def test_logger_writes_to_queue(self):
        run_state = REGISTRY.create("expert")

        logger.log_info(run_state.run_id, "Queue test")

        # Should be able to pop from queue
        event = REGISTRY.pop_next(run_state.run_id, timeout=0.1)
        assert event is not None
        assert event.message == "Queue test"
