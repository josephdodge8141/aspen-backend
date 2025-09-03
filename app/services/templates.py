import re
from typing import List, Dict, Any


TEMPLATE_RE = re.compile(r"\{\{\s*(.*?)\s*\}\}")


def extract_placeholders(text: str) -> List[str]:
    """Extract all placeholders from a template text."""
    matches = TEMPLATE_RE.findall(text)
    return [match.strip() for match in matches]


def validate_placeholders(placeholders: List[str]) -> List[str]:
    """Validate placeholders and return list of warnings/errors for unsupported patterns."""
    errors = []
    warnings = []

    for placeholder in placeholders:
        # Check for empty placeholders
        if not placeholder:
            errors.append("Empty placeholder found: {{}}")
            continue

        # Check for malformed braces (this should be caught by regex, but double-check)
        if "{" in placeholder or "}" in placeholder:
            errors.append(f"Malformed placeholder: {{{{{placeholder}}}}}")
            continue

        # Check for valid roots (base. or input.)
        if not (placeholder.startswith("base.") or placeholder.startswith("input.")):
            warnings.append(
                f"Unknown root in placeholder: {{{{{placeholder}}}}} - should start with 'base.' or 'input.'"
            )
            continue

        # Basic JSONata syntax validation
        # Check for unclosed brackets/parentheses
        open_brackets = placeholder.count("[") - placeholder.count("]")
        open_parens = placeholder.count("(") - placeholder.count(")")

        if open_brackets != 0:
            errors.append(f"Unclosed brackets in placeholder: {{{{{placeholder}}}}}")
        if open_parens != 0:
            errors.append(f"Unclosed parentheses in placeholder: {{{{{placeholder}}}}}")

    return warnings + errors


def validate_template(prompt: str, input_params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a template prompt and return validation results."""
    placeholders = extract_placeholders(prompt)
    validation_errors = validate_placeholders(placeholders)

    # Separate warnings and errors
    warnings = [msg for msg in validation_errors if "Unknown root" in msg]
    errors = [msg for msg in validation_errors if msg not in warnings]

    return {"placeholders": placeholders, "warnings": warnings, "errors": errors}
