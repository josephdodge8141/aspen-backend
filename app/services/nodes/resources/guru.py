from typing import Dict, Any
from pydantic import ValidationError
from app.services.nodes.base import NodeService, NodeValidationError
from app.services.nodes.base_validators import validate_common_fields, validate_no_unknown_fields
from app.services.nodes.models import MetaGuru


class GuruService(NodeService):
    def validate(self, metadata: Dict[str, Any], structured_output: Dict[str, Any]) -> None:
        validate_common_fields(metadata, structured_output)
        
        # Get all possible fields from MetaGuru model
        allowed_fields = set(MetaGuru.model_fields.keys())
        validate_no_unknown_fields(metadata, allowed_fields)
        
        # Validate using Pydantic model
        try:
            MetaGuru(**metadata)
        except ValidationError as e:
            raise NodeValidationError(f"Invalid guru metadata: {e}")
    
    def plan(self, metadata: Dict[str, Any], inputs_shape: Dict[str, Any], structured_output: Dict[str, Any]) -> Dict[str, Any]:
        return {"items": "array"}
    
    def execute(self, inputs: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {"items": []} 