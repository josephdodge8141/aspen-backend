from typing import Dict, Any
from pydantic import ValidationError
from app.services.nodes.base import NodeService, NodeValidationError
from app.services.nodes.base_validators import (
    validate_common_fields,
    validate_no_unknown_fields,
)
from app.services.nodes.models import MetaEmbed


class EmbedService(NodeService):
    def validate(
        self, metadata: Dict[str, Any], structured_output: Dict[str, Any]
    ) -> None:
        validate_common_fields(metadata, structured_output)

        # Get all possible fields from MetaEmbed model
        allowed_fields = set(MetaEmbed.model_fields.keys())
        validate_no_unknown_fields(metadata, allowed_fields)

        # Validate using Pydantic model
        try:
            MetaEmbed(**metadata)
        except ValidationError as e:
            raise NodeValidationError(f"Invalid embed metadata: {e}")

    def plan(
        self,
        metadata: Dict[str, Any],
        inputs_shape: Dict[str, Any],
        structured_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {"embedded": "boolean", "count": "number"}

    def execute(
        self, inputs: Dict[str, Any], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"embedded": True, "count": 1}
