from typing import Dict, Any
from pydantic import ValidationError, BaseModel, create_model
from app.services.nodes.base import NodeService, NodeValidationError
from app.services.nodes.base_validators import (
    validate_common_fields,
    validate_no_unknown_fields,
)
from app.services.nodes.models import MetaJob
from app.services.nodes.util import extract_shape_from_structured_output
from app.services.openai_client import get_openai_service


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
        prompt = metadata.get("prompt", "")
        model_name = metadata.get("model_name", "gpt-4")
        temperature = metadata.get("temperature", 0.7)
        max_tokens = metadata.get("max_tokens")

        if not prompt:
            raise ValueError("Job node requires a 'prompt' in metadata")

        # Check if we need structured output
        if "structured_output" in inputs and inputs["structured_output"]:
            structured_output = inputs["structured_output"]
            shape = extract_shape_from_structured_output(structured_output)

            if shape:
                # Create a dynamic Pydantic model from the shape
                response_model = self._create_response_model(shape)

                try:
                    result = get_openai_service().structured_completion(
                        messages=[{"role": "user", "content": prompt}],
                        response_model=response_model,
                        model=model_name,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    return result
                except Exception as e:
                    # Return error in expected structure
                    return {key: f"Error: {str(e)}" for key in shape.keys()}
            else:
                return {}
        else:
            # Simple text completion
            try:
                response = get_openai_service().generate_text(
                    prompt=prompt,
                    model=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return {"text": response}
            except Exception as e:
                return {"text": f"Error: {str(e)}"}

    def _create_response_model(self, shape: Dict[str, Any]) -> BaseModel:
        fields = {}
        for key, value in shape.items():
            if isinstance(value, dict) and value.get("type") == "string":
                fields[key] = (str, ...)
            elif isinstance(value, dict) and value.get("type") == "number":
                fields[key] = (float, ...)
            elif isinstance(value, dict) and value.get("type") == "integer":
                fields[key] = (int, ...)
            elif isinstance(value, dict) and value.get("type") == "boolean":
                fields[key] = (bool, ...)
            else:
                # Default to string for unknown types
                fields[key] = (str, ...)

        return create_model("DynamicResponse", **fields)
