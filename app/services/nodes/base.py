from typing import Protocol, Dict, Any
from app.models.common import NodeType


class NodeValidationError(ValueError):
    pass


class NodeExecutionError(RuntimeError):
    pass


class NodeService(Protocol):
    def validate(
        self, metadata: Dict[str, Any], structured_output: Dict[str, Any]
    ) -> None:
        pass

    def plan(
        self,
        metadata: Dict[str, Any],
        inputs_shape: Dict[str, Any],
        structured_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        pass

    def execute(
        self, inputs: Dict[str, Any], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        pass


REGISTRY: Dict[NodeType, NodeService] = {}


def get_service(node_type: NodeType) -> NodeService:
    if node_type not in REGISTRY:
        raise ValueError(f"No service registered for node type: {node_type}")
    return REGISTRY[node_type]


def register_service(node_type: NodeType, service: NodeService) -> None:
    REGISTRY[node_type] = service


class DefaultNodeService:
    def validate(
        self, metadata: Dict[str, Any], structured_output: Dict[str, Any]
    ) -> None:
        raise NodeValidationError(
            f"Node service not implemented - validation not available"
        )

    def plan(
        self,
        metadata: Dict[str, Any],
        inputs_shape: Dict[str, Any],
        structured_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        raise NodeExecutionError(
            f"Node service not implemented - planning not available"
        )

    def execute(
        self, inputs: Dict[str, Any], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        raise NodeExecutionError(
            f"Node service not implemented - execution not available"
        )
