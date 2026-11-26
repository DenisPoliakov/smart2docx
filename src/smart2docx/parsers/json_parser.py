"""Разбор smart-документа из JSON."""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from smart2docx.errors import DocumentParseError
from smart2docx.schemas.smart_document import SmartDocument


def parse_json(payload: str | bytes | dict[str, Any]) -> SmartDocument:
    """Преобразует JSON-объект или его текст в `SmartDocument`."""
    if isinstance(payload, dict):
        data: object = payload
    else:
        text = payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DocumentParseError(f"JSON не разобран: {exc.msg}.") from exc
    if not isinstance(data, dict):
        raise DocumentParseError("JSON smart-документа должен быть объектом.")
    return _validate(data)


def _validate(data: dict[str, Any]) -> SmartDocument:
    try:
        return SmartDocument.model_validate(data)
    except ValidationError as exc:
        raise DocumentParseError(_validation_message(exc)) from exc


def _validation_message(exc: ValidationError) -> str:
    parts: list[str] = []
    for error in exc.errors()[:8]:
        location = ".".join(str(item) for item in error["loc"]) or "<корень>"
        parts.append(f"{location}: {error['msg']}")
    suffix = "" if len(exc.errors()) <= 8 else " …"
    return "JSON не соответствует схеме smart-документа: " + "; ".join(parts) + suffix
