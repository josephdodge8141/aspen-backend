from typing import Dict, Any, List
from pydantic import ValidationError
from app.services.nodes.base import NodeService, NodeValidationError
from app.services.nodes.base_validators import (
    validate_common_fields,
    validate_no_unknown_fields,
)
from app.services.nodes.models import MetaIfElse


class IfElseService(NodeService):
    def validate(
        self, metadata: Dict[str, Any], structured_output: Dict[str, Any]
    ) -> None:
        validate_common_fields(metadata, structured_output)

        # Get all possible fields from MetaIfElse model
        allowed_fields = set(MetaIfElse.model_fields.keys())
        validate_no_unknown_fields(metadata, allowed_fields)

        # Validate using Pydantic model
        try:
            MetaIfElse(**metadata)
        except ValidationError as e:
            raise NodeValidationError(f"Invalid if/else metadata: {e}")

    def plan(
        self,
        metadata: Dict[str, Any],
        inputs_shape: Dict[str, Any],
        structured_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        # If/else passes through input shape but adds condition result
        result = inputs_shape.copy() if inputs_shape else {}
        result["condition_result"] = "boolean"
        return result

    def execute(
        self, inputs: Dict[str, Any], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"condition_result": False}
