from typing import Dict, Any
from pydantic import ValidationError
from app.services.nodes.base import NodeService, NodeValidationError
from app.services.nodes.base_validators import validate_common_fields, validate_no_unknown_fields
from app.services.nodes.models import MetaGetAPI


class GetAPIService(NodeService):
    def validate(self, metadata: Dict[str, Any], structured_output: Dict[str, Any]) -> None:
        validate_common_fields(metadata, structured_output)
        
        # Get all possible fields from MetaGetAPI model
        allowed_fields = set(MetaGetAPI.model_fields.keys())
        validate_no_unknown_fields(metadata, allowed_fields)
        
        # Validate using Pydantic model
        try:
            MetaGetAPI(**metadata)
        except ValidationError as e:
            raise NodeValidationError(f"Invalid GET API metadata: {e}")
        
        # Additional validation for JSONata expressions in query_map
        if "query_map" in metadata and metadata["query_map"]:
            for key, value in metadata["query_map"].items():
                if not isinstance(value, str):
                    raise NodeValidationError(f"query_map value for '{key}' must be a string (JSONata expression)")
    
    def plan(self, metadata: Dict[str, Any], inputs_shape: Dict[str, Any], structured_output: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "number", "body": "object"}
    
    def execute(self, inputs: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": 200, "body": {}} 