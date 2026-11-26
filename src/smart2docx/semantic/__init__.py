"""Семантический слой: связный текст по данным smart-документа."""

from smart2docx.semantic.mock_provider import MockSemanticProvider
from smart2docx.semantic.model import NarrativeBlock, SemanticDocument
from smart2docx.semantic.provider import SemanticModelProvider

__all__ = [
    "MockSemanticProvider",
    "NarrativeBlock",
    "SemanticDocument",
    "SemanticModelProvider",
]
