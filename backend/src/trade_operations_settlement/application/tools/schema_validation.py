"""JSON Schema loading, version dispatch, strict validation, and canonical decimal/date normalization.

Provides deterministic validation against versioned JSON Schema definitions without Pydantic.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import jsonschema
from jsonschema.exceptions import ValidationError


class SchemaValidationError(Exception):
    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or [message]


class SchemaValidator:
    def __init__(self) -> None:
        self._schemas: dict[str, dict[str, Any]] = {}

    def register_schema(self, schema_id: str, schema_dict: dict[str, Any]) -> None:
        self._schemas[schema_id] = schema_dict

    def validate(self, schema_id: str, payload: dict[str, Any]) -> None:
        schema = self._schemas.get(schema_id)
        if not schema:
            raise SchemaValidationError(f"Unknown schema identifier: {schema_id}")

        try:
            jsonschema.validate(instance=payload, schema=schema)
        except ValidationError as exc:
            path_str = " -> ".join(str(p) for p in exc.path) if exc.path else "root"
            raise SchemaValidationError(f"Validation failed at '{path_str}': {exc.message}") from exc


def normalize_decimal(value: Any, decimal_places: int = 2) -> str:
    """Normalize numeric value to canonical decimal string representation."""
    if isinstance(value, Decimal):
        dec = value
    elif isinstance(value, (int, float, str)):
        try:
            dec = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError(f"Cannot convert {value} to Decimal") from exc
    else:
        raise TypeError(f"Unsupported decimal type: {type(value)}")

    fmt = f"{{:.{decimal_places}f}}"
    return fmt.format(dec)


def normalize_iso_date(value: Any) -> str:
    """Normalize date/datetime to canonical ISO 8601 string."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        # Validate parseability
        try:
            dt = datetime.fromisoformat(value)
            return dt.isoformat()
        except ValueError as exc:
            raise ValueError(f"Invalid ISO date string: {value}") from exc
    raise TypeError(f"Unsupported date type: {type(value)}")
