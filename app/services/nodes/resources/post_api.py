from typing import Dict, Any
from pydantic import ValidationError
from app.services.nodes.base import NodeService, NodeValidationError
from app.services.nodes.base_validators import (
    validate_common_fields,
    validate_no_unknown_fields,
)
from app.services.nodes.models import MetaPostAPI


class PostAPIService(NodeService):
    def validate(
        self, metadata: Dict[str, Any], structured_output: Dict[str, Any]
    ) -> None:
        validate_common_fields(metadata, structured_output)

        # Get all possible fields from MetaPostAPI model
        allowed_fields = set(MetaPostAPI.model_fields.keys())
        validate_no_unknown_fields(metadata, allowed_fields)

        # Validate using Pydantic model
        try:
            MetaPostAPI(**metadata)
        except ValidationError as e:
            raise NodeValidationError(f"Invalid POST API metadata: {e}")

        # Additional validation for JSONata expressions in body_map
        if "body_map" in metadata and metadata["body_map"]:
            self._validate_body_map(metadata["body_map"])

    def _validate_body_map(self, body_map: Dict[str, Any], path: str = "") -> None:
        for key, value in body_map.items():
            current_path = f"{path}.{key}" if path else key

            if isinstance(value, dict):
                self._validate_body_map(value, current_path)
            elif isinstance(value, str):
                # JSONata expression - just validate it's a string for now
                pass
            elif isinstance(value, (int, float, bool, type(None))):
                # Literal values are allowed
                pass
            else:
                raise NodeValidationError(
                    f"body_map value at '{current_path}' must be a string (JSONata), literal value, or nested object"
                )

    def plan(
        self,
        metadata: Dict[str, Any],
        inputs_shape: Dict[str, Any],
        structured_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {"status": "number", "body": "object"}

    def execute(
        self, inputs: Dict[str, Any], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"status": 200, "body": {}}
