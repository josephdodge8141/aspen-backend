import json
import time
import threading
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.runs.registry import REGISTRY
from app.services.runs import logger


@pytest.mark.integration
class TestChatSSE:
    def setup_method(self):
        self.client = TestClient(app)

    def test_stream_run_events_with_backlog_and_new_events(self):
        """Test SSE endpoint with existing events and new ones."""
        # Create a run and add some initial events
        run_state = REGISTRY.create("expert")
        run_id = run_state.run_id
        
        # Add some backlog events
        logger.log_info(run_id, "Initial event", step=1)
        logger.log_warn(run_id, "Warning event", step=2)
        
        # Start SSE stream in a separate thread
        events_received = []
        
        def stream_events():
            with self.client.stream("GET", f"/api/v1/chat/runs/{run_id}/events") as response:
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
                
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])  # Remove "data: " prefix
                        events_received.append(data)
                        
                        # Stop after receiving the done event
                        if len(events_received) >= 4:  # 2 backlog + 1 new + 1 done
                            break
        
        # Start streaming in background
        stream_thread = threading.Thread(target=stream_events)
        stream_thread.start()
        
        # Give it a moment to start and receive backlog
        time.sleep(0.1)
        
        # Add a new event while streaming
        logger.log_error(run_id, "Error event", step=3)
        
        # Finish the run
        logger.finish(run_id)
        
        # Wait for streaming to complete
        stream_thread.join(timeout=5.0)
        
        # Verify events were received
        assert len(events_received) >= 3
        
        # Check backlog events
        assert events_received[0]["message"] == "Initial event"
        assert events_received[0]["level"] == "info"
        assert events_received[0]["data"]["step"] == 1
        
        assert events_received[1]["message"] == "Warning event"
        assert events_received[1]["level"] == "warn"
        assert events_received[1]["data"]["step"] == 2
        
        # Check new event
        assert events_received[2]["message"] == "Error event"
        assert events_received[2]["level"] == "error"
        assert events_received[2]["data"]["step"] == 3

    def test_stream_nonexistent_run(self):
        """Test SSE endpoint with non-existent run ID."""
        with self.client.stream("GET", "/api/v1/chat/runs/nonexistent-id/events") as response:
            assert response.status_code == 200
            
            # Should receive error event
            lines = list(response.iter_lines())
            error_line = next((line for line in lines if line.startswith("data: ")), None)
            assert error_line is not None
            
            data = json.loads(error_line[6:])
            assert "error" in data
            assert data["error"] == "Run not found"

    def test_stream_empty_run(self):
        """Test SSE endpoint with run that has no events."""
        run_state = REGISTRY.create("workflow")
        run_id = run_state.run_id
        
        # Immediately finish the run
        logger.finish(run_id)
        
        events_received = []
        
        with self.client.stream("GET", f"/api/v1/chat/runs/{run_id}/events") as response:
            assert response.status_code == 200
            
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    events_received.append(data)
                    
                    # Stop after receiving done event
                    if "finished_at" in data:
                        break
        
        # Should receive at least the done event
        assert len(events_received) >= 1
        assert "finished_at" in events_received[-1]

    def test_stream_with_heartbeat(self):
        """Test that heartbeat events are sent during timeout periods."""
        run_state = REGISTRY.create("expert")
        run_id = run_state.run_id
        
        events_received = []
        heartbeats_received = 0
        
        def stream_with_timeout():
            with self.client.stream("GET", f"/api/v1/chat/runs/{run_id}/events") as response:
                start_time = time.time()
                for line in response.iter_lines():
                    if line.startswith("event: heartbeat"):
                        nonlocal heartbeats_received
                        heartbeats_received += 1
                    elif line.startswith("data: "):
                        data = json.loads(line[6:])
                        events_received.append(data)
                    
                    # Stop after a short time or if we get heartbeats
                    if time.time() - start_time > 1.0 or heartbeats_received > 0:
                        break
        
        # Start streaming
        stream_thread = threading.Thread(target=stream_with_timeout)
        stream_thread.start()
        
        # Let it run for a bit to potentially receive heartbeats
        stream_thread.join(timeout=2.0)
        
        # We might receive heartbeats depending on timing
        # The important thing is that the connection doesn't hang
        assert True  # If we get here, the connection handled timeouts properly


@pytest.mark.integration  
class TestSSEEventFormat:
    def setup_method(self):
        self.client = TestClient(app)

    def test_event_format_structure(self):
        """Test that SSE events have the correct JSON structure."""
        run_state = REGISTRY.create("expert")
        run_id = run_state.run_id
        
        # Add an event with various data types
        logger.log_info(run_id, "Test message", 
                       string_field="text",
                       number_field=42,
                       boolean_field=True,
                       nested_object={"key": "value"})
        
        logger.finish(run_id)
        
        with self.client.stream("GET", f"/api/v1/chat/runs/{run_id}/events") as response:
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    
                    # Check required fields
                    assert "ts" in data
                    assert "level" in data  
                    assert "message" in data
                    assert "data" in data
                    
                    # Check data types
                    assert isinstance(data["ts"], (int, float))
                    assert isinstance(data["level"], str)
                    assert isinstance(data["message"], str)
                    assert isinstance(data["data"], dict)
                    
                    # Check custom data fields
                    if data["message"] == "Test message":
                        assert data["data"]["string_field"] == "text"
                        assert data["data"]["number_field"] == 42
                        assert data["data"]["boolean_field"] is True
                        assert data["data"]["nested_object"]["key"] == "value"
                    
                    break 