from typing import Dict, Any
from pydantic import ValidationError
from app.services.nodes.base import NodeService, NodeValidationError
from app.services.nodes.base_validators import (
    validate_common_fields,
    validate_no_unknown_fields,
)
from app.services.nodes.models import MetaJob
from app.services.nodes.util import extract_shape_from_structured_output


class JobService(NodeService):
    def validate(
        self, metadata: Dict[str, Any], structured_output: Dict[str, Any]
    ) -> None:
        validate_common_fields(metadata, structured_output)

        # Get all possible fields from MetaJob model
        allowed_fields = set(MetaJob.model_fields.keys())
        validate_no_unknown_fields(metadata, allowed_fields)

        # Validate using Pydantic model
        try:
            MetaJob(**metadata)
        except ValidationError as e:
            raise NodeValidationError(f"Invalid job metadata: {e}")

    def plan(
        self,
        metadata: Dict[str, Any],
        inputs_shape: Dict[str, Any],
        structured_output: Dict[str, Any],
    ) -> Dict[str, Any]:
        if structured_output:
            return extract_shape_from_structured_output(structured_output)
        else:
            return {"text": "string"}

    def execute(
        self, inputs: Dict[str, Any], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        if "structured_output" in inputs and inputs["structured_output"]:
            shape = extract_shape_from_structured_output(inputs["structured_output"])
            return {key: None for key in shape.keys()} if shape else {}
        else:
            return {"text": None}
