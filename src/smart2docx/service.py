"""Сборка документа: разбор уже выполнен, остаются шаблон, текст и DOCX."""

from __future__ import annotations

import re
from dataclasses import dataclass

from smart2docx.builder.docx_builder import DOCX_MEDIA_TYPE, DocxBuilder
from smart2docx.schemas.generation import GenerationOptions
from smart2docx.schemas.smart_document import SmartDocument
from smart2docx.semantic.mock_provider import MockSemanticProvider
from smart2docx.semantic.provider import SemanticModelProvider
from smart2docx.templates.profile import TemplateProfile
from smart2docx.templates.registry import TemplateRegistry

_FILENAME_UNSAFE = re.compile(r"[^\w.-]+", re.UNICODE)


@dataclass(frozen=True)
class GeneratedDocument:
    """Готовый файл и имя, которое отдаётся вызывающей системе."""

    filename: str
    content: bytes
    media_type: str = DOCX_MEDIA_TYPE


def generate_document(
    document: SmartDocument,
    template_id: str,
    *,
    provider: SemanticModelProvider | None = None,
    registry: TemplateRegistry | None = None,
    options: GenerationOptions | None = None,
) -> GeneratedDocument:
    """Прогоняет smart-документ через семантический слой и собирает DOCX."""
    options = options or GenerationOptions()
    profile = (registry or TemplateRegistry()).get(template_id)
    semantic = (provider or MockSemanticProvider()).render(document, profile, options)
    content = DocxBuilder().build(semantic, profile, options)
    return GeneratedDocument(filename=build_filename(profile, document), content=content)


def build_filename(profile: TemplateProfile, document: SmartDocument) -> str:
    """Собирает имя файла из префикса шаблона и обозначения документа."""
    raw = document.metadata.document_cipher or document.metadata.object_code or "document"
    cleaned = _FILENAME_UNSAFE.sub("_", raw).strip("._") or "document"
    return f"{profile.filename_prefix}_{cleaned}.docx"
