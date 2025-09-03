from typing import Dict, Any
from pydantic import ValidationError
from app.services.nodes.base import NodeService, NodeValidationError
from app.services.nodes.base_validators import validate_common_fields, validate_no_unknown_fields
from app.services.nodes.models import MetaMerge


class MergeService(NodeService):
    def validate(self, metadata: Dict[str, Any], structured_output: Dict[str, Any]) -> None:
        validate_common_fields(metadata, structured_output)
        
        # Get all possible fields from MetaMerge model
        allowed_fields = set(MetaMerge.model_fields.keys())
        validate_no_unknown_fields(metadata, allowed_fields)
        
        # Validate using Pydantic model
        try:
            MetaMerge(**metadata)
        except ValidationError as e:
            raise NodeValidationError(f"Invalid merge metadata: {e}")
    
    def plan(self, metadata: Dict[str, Any], inputs_shape: Dict[str, Any], structured_output: Dict[str, Any]) -> Dict[str, Any]:
        # Merge combines parent shapes - for planning, we assume union strategy
        # In real execution, this would be computed from actual parent outputs
        result = inputs_shape.copy() if inputs_shape else {}
        result["merged_data"] = "object"
        return result
    
    def execute(self, inputs: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {"merged_data": {}} 