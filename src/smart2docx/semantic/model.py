"""Результат семантического слоя: разделы, готовые к записи в DOCX."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from smart2docx.schemas.smart_document import CharacteristicTable


class NarrativeBlock(BaseModel):
    """Заголовок, абзацы и таблицы одного раздела."""

    model_config = ConfigDict(extra="ignore")

    code: str
    heading: str
    level: int = 1
    paragraphs: list[str] = Field(default_factory=list)
    tables: list[CharacteristicTable] = Field(default_factory=list)
    children: list[NarrativeBlock] = Field(default_factory=list)


class SemanticDocument(BaseModel):
    """Текстовое представление smart-документа в рамках выбранного шаблона."""

    model_config = ConfigDict(extra="ignore")

    template_id: str
    title: str
    document_kind: str
    object_name: str
    document_cipher: str | None = None
    designer: str | None = None
    customer: str | None = None
    address: str | None = None
    project_stage: str | None = None
    year: int | None = None
    normative_basis: list[str] = Field(default_factory=list)
    blocks: list[NarrativeBlock] = Field(default_factory=list)


NarrativeBlock.model_rebuild()
