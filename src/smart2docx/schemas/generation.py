"""Параметры запроса на формирование документа."""

from __future__ import annotations

from pydantic import Field

from smart2docx.schemas.base import SchemaModel
from smart2docx.schemas.smart_document import SmartDocument


class GenerationOptions(SchemaModel):
    """Параметры сборки, не меняющие профиль шаблона."""

    include_title_page: bool = True


class GenerationRequest(SchemaModel):
    """JSON-запрос: идентификатор шаблона и smart-документ."""

    template_id: str = Field(min_length=1)
    document: SmartDocument
    options: GenerationOptions = Field(default_factory=GenerationOptions)
