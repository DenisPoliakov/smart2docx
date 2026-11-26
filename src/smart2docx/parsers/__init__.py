"""Разбор JSON и XML в единую модель smart-документа."""

from __future__ import annotations

from smart2docx.errors import DocumentParseError
from smart2docx.parsers.json_parser import parse_json
from smart2docx.parsers.xml_parser import parse_xml
from smart2docx.schemas.smart_document import SmartDocument


def parse_document(
    payload: str | bytes,
    *,
    kind: str | None = None,
    filename: str | None = None,
    content_type: str | None = None,
) -> SmartDocument:
    """Разбирает текст smart-документа.

    Формат берётся из `kind` (`json` или `xml`), иначе определяется
    по типу содержимого, имени файла и первому значащему символу.
    """
    try:
        if isinstance(payload, bytes):
            text = payload.decode("utf-8-sig")
            raw: str | bytes = payload
        else:
            text = payload
            raw = payload
    except UnicodeDecodeError as exc:
        raise DocumentParseError("Документ должен быть в кодировке UTF-8.") from exc
    detected = (kind or _detect(text, filename=filename, content_type=content_type)).lower()
    if detected == "json":
        return parse_json(text if isinstance(payload, str) else raw)
    if detected == "xml":
        return parse_xml(text if isinstance(payload, str) else raw)
    raise DocumentParseError("Формат не поддержан. Ожидается JSON или XML.")


def _detect(text: str, *, filename: str | None, content_type: str | None) -> str:
    if content_type:
        lowered = content_type.lower()
        if "json" in lowered:
            return "json"
        if "xml" in lowered:
            return "xml"
    if filename and "." in filename:
        suffix = filename.rsplit(".", 1)[-1].lower()
        if suffix in {"json", "xml"}:
            return suffix
    stripped = text.lstrip("\ufeff \t\r\n")
    if stripped.startswith("<"):
        return "xml"
    if stripped.startswith("{") or stripped.startswith("["):
        return "json"
    raise DocumentParseError("Формат не распознан. Ожидается JSON или XML.")


__all__ = ["parse_document", "parse_json", "parse_xml"]
