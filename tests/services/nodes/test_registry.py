import pytest
from app.services.nodes.base import (
    NodeService,
    NodeValidationError,
    NodeExecutionError,
    REGISTRY,
    get_service,
    register_service,
    DefaultNodeService,
)
from app.models.common import NodeType


class MockNodeService:
    def validate(self, metadata, structured_output):
        if not metadata.get("valid", True):
            raise NodeValidationError("Mock validation error")

    def plan(self, metadata, inputs_shape, structured_output):
        return {"mock": "plan"}

    def execute(self, inputs, metadata):
        return {"mock": "execution"}


class TestNodeServiceRegistry:
    def setup_method(self):
        REGISTRY.clear()

    def teardown_method(self):
        REGISTRY.clear()

    def test_register_and_get_service(self):
        mock_service = MockNodeService()
        register_service(NodeType.job, mock_service)

        retrieved_service = get_service(NodeType.job)
        assert retrieved_service is mock_service

    def test_get_unregistered_service_raises_error(self):
        with pytest.raises(
            ValueError, match="No service registered for node type: NodeType.job"
        ):
            get_service(NodeType.job)

    def test_registry_isolation(self):
        mock_service = MockNodeService()
        register_service(NodeType.job, mock_service)

        assert NodeType.job in REGISTRY
        assert NodeType.guru not in REGISTRY

        with pytest.raises(ValueError):
            get_service(NodeType.guru)

    def test_service_protocol_methods(self):
        mock_service = MockNodeService()
        register_service(NodeType.job, mock_service)

        service = get_service(NodeType.job)

        service.validate({"valid": True}, {})

        with pytest.raises(NodeValidationError, match="Mock validation error"):
            service.validate({"valid": False}, {})

        plan_result = service.plan({}, {}, {})
        assert plan_result == {"mock": "plan"}

        exec_result = service.execute({}, {})
        assert exec_result == {"mock": "execution"}


class TestDefaultNodeService:
    def test_default_service_validation_raises_error(self):
        service = DefaultNodeService()

        with pytest.raises(
            NodeValidationError,
            match="Node service not implemented - validation not available",
        ):
            service.validate({}, {})

    def test_default_service_plan_raises_error(self):
        service = DefaultNodeService()

        with pytest.raises(
            NodeExecutionError,
            match="Node service not implemented - planning not available",
        ):
            service.plan({}, {}, {})

    def test_default_service_execute_raises_error(self):
        service = DefaultNodeService()

        with pytest.raises(
            NodeExecutionError,
            match="Node service not implemented - execution not available",
        ):
            service.execute({}, {})
