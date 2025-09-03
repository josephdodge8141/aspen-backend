import re
from typing import Dict, Any, List, Tuple
from app.lib.jsonata import safe_evaluate_jsonata


def render_prompt(template: str, base: Dict[str, Any], input_data: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    Render a prompt template by replacing {{ ... }} placeholders with values.
    
    Args:
        template: The prompt template with {{ ... }} placeholders
        base: Base values (accessed via base.*)
        input_data: Input data (accessed via input.*)
        
    Returns:
        Tuple of (rendered_prompt, warnings)
    """
    warnings = []
    
    # Find all placeholders in the format {{ ... }}
    placeholder_pattern = r'\{\{\s*([^}]+)\s*\}\}'
    
    def replace_placeholder(match):
        expression = match.group(1).strip()
        
        # Determine the data source and JSONata expression
        if expression.startswith('base.'):
            # Remove 'base.' prefix and evaluate against base data
            jsonata_expr = expression[5:]  # Remove 'base.'
            result = safe_evaluate_jsonata(jsonata_expr, base, default=None)
        elif expression.startswith('input.'):
            # Remove 'input.' prefix and evaluate against input data
            jsonata_expr = expression[6:]  # Remove 'input.'
            result = safe_evaluate_jsonata(jsonata_expr, input_data, default=None)
        else:
            # Try to evaluate as-is against input data first, then base
            result = safe_evaluate_jsonata(expression, input_data, default=None)
            if result is None:
                result = safe_evaluate_jsonata(expression, base, default=None)
        
        if result is None:
            warnings.append(f"Could not resolve placeholder: {{{{{expression}}}}}")
            return match.group(0)  # Return original placeholder
        
        return str(result)
    
    rendered = re.sub(placeholder_pattern, replace_placeholder, template)
    return rendered, warnings


def get_base_defaults() -> Dict[str, Any]:
    """Get default base values for prompt rendering."""
    import datetime
    import time
    
    now = datetime.datetime.now()
    
    return {
        "timestamp": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timezone": str(now.astimezone().tzinfo),
        "unix_timestamp": int(time.time()),
        "day_of_week": now.strftime("%A"),
        "month": now.strftime("%B"),
        "year": now.year
    } 