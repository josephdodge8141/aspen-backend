from typing import Dict, Any, Union
import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError
from app.services.nodes.base import NodeValidationError


def validate_structured_output(structured_output: Dict[str, Any]) -> None:
    if not isinstance(structured_output, dict):
        raise NodeValidationError("structured_output must be a dictionary")
    
    if not structured_output:
        return
    
    try:
        if "type" in structured_output:
            jsonschema.Draft7Validator.check_schema(structured_output)
    except JsonSchemaValidationError as e:
        raise NodeValidationError(f"Invalid JSON schema in structured_output: {e.message}")


def extract_shape_from_structured_output(structured_output: Dict[str, Any]) -> Dict[str, Any]:
    if not structured_output:
        return {}
    
    if structured_output.get("type") == "object" and "properties" in structured_output:
        shape = {}
        for key, prop_schema in structured_output["properties"].items():
            shape[key] = _get_type_from_schema(prop_schema)
        return shape
    elif structured_output.get("type") == "array":
        return {"type": "array"}
    else:
        return {"type": structured_output.get("type", "unknown")}


def _get_type_from_schema(schema: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
    schema_type = schema.get("type", "unknown")
    
    if schema_type == "object" and "properties" in schema:
        nested_shape = {}
        for key, prop_schema in schema["properties"].items():
            nested_shape[key] = _get_type_from_schema(prop_schema)
        return nested_shape
    elif schema_type == "array":
        if "items" in schema:
            return {"type": "array", "items": _get_type_from_schema(schema["items"])}
        return {"type": "array"}
    else:
        return schema_type


def coerce_to_shape(data: Any) -> Dict[str, str]:
    if isinstance(data, dict):
        return {key: _type_name(value) for key, value in data.items()}
    else:
        return {"type": _type_name(data)}


def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    elif isinstance(value, int):
        return "number"
    elif isinstance(value, float):
        return "number"
    elif isinstance(value, str):
        return "string"
    elif isinstance(value, list):
        return "array"
    elif isinstance(value, dict):
        return "object"
    elif value is None:
        return "null"
    else:
        return "unknown" 