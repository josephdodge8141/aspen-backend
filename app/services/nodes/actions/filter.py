from typing import Dict, Any
from pydantic import ValidationError
from app.services.nodes.base import NodeService, NodeValidationError
from app.services.nodes.base_validators import validate_common_fields, validate_no_unknown_fields
from app.services.nodes.models import MetaFilter


class FilterService(NodeService):
    def validate(self, metadata: Dict[str, Any], structured_output: Dict[str, Any]) -> None:
        validate_common_fields(metadata, structured_output)
        
        # Get all possible fields from MetaFilter model
        allowed_fields = set(MetaFilter.model_fields.keys())
        validate_no_unknown_fields(metadata, allowed_fields)
        
        # Validate using Pydantic model
        try:
            MetaFilter(**metadata)
        except ValidationError as e:
            raise NodeValidationError(f"Invalid filter metadata: {e}")
    
    def plan(self, metadata: Dict[str, Any], inputs_shape: Dict[str, Any], structured_output: Dict[str, Any]) -> Dict[str, Any]:
        # Filter passes through the input shape unchanged (just filters items)
        return inputs_shape
    
    def execute(self, inputs: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {} 