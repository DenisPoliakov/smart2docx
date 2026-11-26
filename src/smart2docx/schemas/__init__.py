"""Схемы smart-документа и запроса генерации."""

from smart2docx.schemas.generation import GenerationOptions, GenerationRequest
from smart2docx.schemas.smart_document import (
    CharacteristicTable,
    Parameter,
    ProjectMetadata,
    Requirement,
    SmartDocument,
    SmartSection,
    TableColumn,
)

__all__ = [
    "CharacteristicTable",
    "GenerationOptions",
    "GenerationRequest",
    "Parameter",
    "ProjectMetadata",
    "Requirement",
    "SmartDocument",
    "SmartSection",
    "TableColumn",
]
