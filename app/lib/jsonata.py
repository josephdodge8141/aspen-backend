from typing import Any, Dict, Optional
import signal
from contextlib import contextmanager
from jsonata import Jsonata


class JSONataError(Exception):
    def __init__(self, message: str, expression: str, path: Optional[str] = None):
        self.message = message
        self.expression = expression
        self.path = path
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        if self.path:
            return f"JSONata error at '{self.path}': {self.message} (expression: {self.expression})"
        else:
            return f"JSONata error: {self.message} (expression: {self.expression})"


class JSONataTimeoutError(JSONataError):
    def __init__(
        self, expression: str, timeout_seconds: float, path: Optional[str] = None
    ):
        super().__init__(
            f"Evaluation timed out after {timeout_seconds}s", expression, path
        )


@contextmanager
def timeout_handler(timeout_seconds: float):
    def timeout_signal_handler(signum, frame):
        raise TimeoutError()

    old_handler = signal.signal(signal.SIGALRM, timeout_signal_handler)
    signal.alarm(int(timeout_seconds))

    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def evaluate_jsonata(
    expression: str,
    data: Dict[str, Any],
    timeout_seconds: float = 5.0,
    path: Optional[str] = None,
) -> Any:
    if not isinstance(expression, str):
        raise JSONataError("Expression must be a string", str(expression), path)

    if not expression.strip():
        raise JSONataError("Expression cannot be empty", expression, path)

    try:
        # Parse the JSONata expression
        jsonata_expr = Jsonata(expression)

        # Evaluate with timeout
        with timeout_handler(timeout_seconds):
            result = jsonata_expr.evaluate(data)

        return result

    except TimeoutError:
        raise JSONataTimeoutError(expression, timeout_seconds, path)
    except Exception as e:
        # Wrap any other errors from the JSONata library
        raise JSONataError(f"Evaluation failed: {str(e)}", expression, path)


def validate_jsonata_syntax(expression: str, path: Optional[str] = None) -> None:
    if not isinstance(expression, str):
        raise JSONataError("Expression must be a string", str(expression), path)

    if not expression.strip():
        raise JSONataError("Expression cannot be empty", expression, path)

    try:
        # Just parse to check syntax - don't evaluate
        Jsonata(expression)
    except Exception as e:
        raise JSONataError(f"Syntax error: {str(e)}", expression, path)


def safe_evaluate_jsonata(
    expression: str,
    data: Dict[str, Any],
    default: Any = None,
    timeout_seconds: float = 5.0,
    path: Optional[str] = None,
) -> Any:
    try:
        return evaluate_jsonata(expression, data, timeout_seconds, path)
    except JSONataError:
        return default
