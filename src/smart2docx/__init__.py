"""Модуль формирования документов DOCX по ГОСТ на основе smart-документов."""

__version__ = "0.1.0"

from smart2docx.service import GeneratedDocument, generate_document

__all__ = ["GeneratedDocument", "__version__", "generate_document"]
