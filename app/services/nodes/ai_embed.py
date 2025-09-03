from typing import Dict, Any
from pydantic import ValidationError
from app.services.nodes.base import NodeService, NodeValidationError
from app.services.nodes.base_validators import (
    validate_common_fields,
    validate_no_unknown_fields,
)
from app.services.nodes.models import MetaEmbed
from app.services.openai_client import get_openai_service


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
        input_text = inputs.get("input", "")
        model_name = metadata.get("model_name", "text-embedding-3-small")
        
        if not input_text:
            return {"embedding": [], "error": "No input text provided"}
        
        try:
            response = get_openai_service().client.embeddings.create(
                model=model_name,
                input=input_text
            )
            embedding = response.data[0].embedding
            
            return {
                "embedding": embedding,
                "dimensions": len(embedding),
                "model": model_name,
                "input_length": len(input_text)
            }
        except Exception as e:
            return {
                "embedding": [],
                "error": f"Failed to create embedding: {str(e)}"
            }
