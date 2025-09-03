from croniter import croniter


def is_valid_cron(expr: str) -> bool:
    """
    Validate a cron expression using croniter.

    Args:
        expr: The cron expression to validate

    Returns:
        True if the expression is valid, False otherwise
    """
    if not isinstance(expr, str):
        return False

    try:
        croniter(expr)
        return True
    except (ValueError, TypeError, AttributeError):
        return False
