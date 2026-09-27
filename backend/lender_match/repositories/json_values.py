from typing import Any

from pydantic_core import to_jsonable_python


def to_json_safe(value: Any) -> Any:
    """Convert a value for a jsonb column: Decimal to str, date to an
    ISO string, Pydantic objects to plain dicts.
    """
    return to_jsonable_python(value)
