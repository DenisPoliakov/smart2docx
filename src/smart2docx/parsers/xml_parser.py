"""Разбор smart-документа из XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from pydantic import ValidationError

from smart2docx.errors import DocumentParseError
from smart2docx.schemas.smart_document import SmartDocument


def parse_xml(payload: str | bytes) -> SmartDocument:
    """Преобразует XML smart-документа в `SmartDocument`.

    Пространства имён игнорируются. Имена элементов принимаются
    в camelCase и snake_case. Значения задаются атрибутами или вложенными элементами.
    """
    source = _as_bytes(payload)
    try:
        root = ET.fromstring(source)
    except ET.ParseError as exc:
        raise DocumentParseError(f"XML не разобран: {exc}.") from exc
    if _local(root.tag) not in {"smartdocument", "document"}:
        raise DocumentParseError("Корневой элемент XML должен быть smartDocument.")
    try:
        return SmartDocument.model_validate(_document_dict(root))
    except ValidationError as exc:
        parts = []
        for error in exc.errors()[:8]:
            location = ".".join(str(item) for item in error["loc"]) or "<корень>"
            parts.append(f"{location}: {error['msg']}")
        raise DocumentParseError(
            "XML не соответствует схеме smart-документа: " + "; ".join(parts)
        ) from exc
    except DocumentParseError:
        raise


def _as_bytes(payload: str | bytes) -> bytes:
    if isinstance(payload, bytes):
        if payload.startswith(b"\xef\xbb\xbf"):
            return payload[3:]
        return payload
    return payload.lstrip("\ufeff").encode("utf-8")


def _local(tag: str) -> str:
    if "}" in tag:
        tag = tag.rsplit("}", 1)[-1]
    return tag.replace("-", "").replace("_", "").lower()


def _raw_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(element) if _local(child.tag) == name]


def _child(element: ET.Element, name: str) -> ET.Element | None:
    found = _children(element, name)
    return found[0] if found else None


def _first_child(element: ET.Element, *names: str) -> ET.Element | None:
    for name in names:
        found = _child(element, name)
        if found is not None:
            return found
    return None


def _direct_text(element: ET.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _attr(element: ET.Element, *names: str) -> str | None:
    wanted = {_local(name) for name in names}
    for key, value in element.attrib.items():
        if _local(key) in wanted and value.strip():
            return value.strip()
    return None


def _value(element: ET.Element, *names: str) -> str | None:
    for name in names:
        text = _direct_text(_child(element, name))
        if text:
            return text
    return _attr(element, *names)


def _optional_int(value: str | None, field: str) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise DocumentParseError(f"Поле {field} должно быть целым числом.") from exc


def _document_dict(root: ET.Element) -> dict[str, object]:
    metadata = _first_child(root, "metadata", "meta")
    if metadata is None:
        raise DocumentParseError("В XML отсутствует элемент metadata.")
    sections_node = _child(root, "sections")
    if sections_node is not None:
        section_nodes = _children(sections_node, "section")
    else:
        section_nodes = _children(root, "section")
    return {
        "document_type": _value(root, "documenttype", "documentType"),
        "metadata": _metadata_dict(metadata),
        "sections": [_section_dict(node) for node in section_nodes],
    }


def _metadata_dict(element: ET.Element) -> dict[str, object]:
    return {
        "object_name": _value(element, "objectname", "objectName", "name"),
        "object_code": _value(element, "objectcode", "objectCode"),
        "document_cipher": _value(element, "documentcipher", "documentCipher", "cipher"),
        "project_stage": _value(element, "projectstage", "projectStage", "stage"),
        "address": _value(element, "address"),
        "customer": _value(element, "customer"),
        "designer": _value(element, "designer"),
        "chief_engineer": _value(element, "chiefengineer", "chiefEngineer"),
        "year": _optional_int(_value(element, "year"), "year"),
    }


def _section_dict(element: ET.Element) -> dict[str, object]:
    subsections_node = _child(element, "subsections")
    if subsections_node is not None:
        subsection_nodes = _children(subsections_node, "section")
    else:
        subsection_nodes = _children(element, "section")
    return {
        "code": _value(element, "code"),
        "title": _value(element, "title"),
        "content": _content_text(element),
        "parameters": _parameters(element),
        "requirements": _requirements(element),
        "tables": _tables(element),
        "subsections": [_section_dict(node) for node in subsection_nodes],
    }


def _content_text(element: ET.Element) -> str | None:
    node = _first_child(element, "content", "text")
    if node is None:
        return None
    chunks: list[str] = []
    if node.text and node.text.strip():
        chunks.append(node.text.strip())
    for child in list(node):
        if _local(child.tag) in {"p", "paragraph"}:
            paragraph = (child.text or "").strip()
            if paragraph:
                chunks.append(paragraph)
        elif child.tail and child.tail.strip():
            chunks.append(child.tail.strip())
    text = "\n\n".join(chunks).strip()
    return text or None


def _parameters(section: ET.Element) -> list[dict[str, object]]:
    container = _child(section, "parameters")
    nodes = _children(container, "parameter") if container is not None else _children(section, "parameter")
    return [
        {
            "name": _value(node, "name"),
            "value": _value(node, "value"),
            "unit": _value(node, "unit"),
            "note": _value(node, "note"),
        }
        for node in nodes
    ]


def _requirements(section: ET.Element) -> list[dict[str, object]]:
    container = _child(section, "requirements")
    nodes = (
        _children(container, "requirement") if container is not None else _children(section, "requirement")
    )
    items: list[dict[str, object]] = []
    for node in nodes:
        text = _value(node, "text")
        if text is None:
            text = (node.text or "").strip() or None
        items.append(
            {
                "text": text,
                "code": _attr(node, "code") or _value(node, "code"),
                "source": _attr(node, "source") or _value(node, "source"),
            }
        )
    return items


def _tables(section: ET.Element) -> list[dict[str, object]]:
    container = _child(section, "tables")
    nodes = _children(container, "table") if container is not None else _children(section, "table")
    return [_table_dict(node) for node in nodes]


def _table_dict(table: ET.Element) -> dict[str, object]:
    columns_node = _child(table, "columns")
    column_nodes = (
        _children(columns_node, "column") if columns_node is not None else _children(table, "column")
    )
    columns = []
    for column in column_nodes:
        title = _value(column, "title") or (column.text or "").strip() or None
        columns.append({"key": _value(column, "key"), "title": title})
    rows_node = _child(table, "rows")
    row_nodes = _children(rows_node, "row") if rows_node is not None else _children(table, "row")
    return {
        "title": _value(table, "title"),
        "columns": columns,
        "rows": [_row_dict(row) for row in row_nodes],
    }


def _row_dict(row: ET.Element) -> dict[str, str]:
    cells = _children(row, "cell")
    if cells:
        record: dict[str, str] = {}
        for cell in cells:
            key = _value(cell, "key") or _attr(cell, "key")
            if not key:
                continue
            value = (cell.text or "").strip()
            record[key] = value
        return record
    return {_raw_name(key): value.strip() for key, value in row.attrib.items()}
