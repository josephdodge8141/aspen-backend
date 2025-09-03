from typing import Dict, Any
from app.services.nodes.base import NodeValidationError
from app.services.nodes.util import validate_structured_output


def validate_common_fields(
    metadata: Dict[str, Any], structured_output: Dict[str, Any]
) -> None:
    if not isinstance(metadata, dict):
        raise NodeValidationError("metadata must be a dictionary")

    if not isinstance(structured_output, dict):
        raise NodeValidationError("structured_output must be a dictionary")

    validate_structured_output(structured_output)


def validate_no_unknown_fields(metadata: Dict[str, Any], allowed_fields: set) -> None:
    unknown_fields = set(metadata.keys()) - allowed_fields
    if unknown_fields:
        raise NodeValidationError(
            f"Unknown fields in metadata: {', '.join(sorted(unknown_fields))}"
        )


def validate_required_fields(metadata: Dict[str, Any], required_fields: set) -> None:
    missing_fields = required_fields - set(metadata.keys())
    if missing_fields:
        raise NodeValidationError(
            f"Missing required fields: {', '.join(sorted(missing_fields))}"
        )


def validate_non_empty_string(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise NodeValidationError(f"{field_name} must be a non-empty string")
