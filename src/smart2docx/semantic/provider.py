"""Контракт поставщика связного текста."""

from __future__ import annotations

from abc import ABC, abstractmethod

from smart2docx.schemas.generation import GenerationOptions
from smart2docx.schemas.smart_document import SmartDocument
from smart2docx.semantic.model import SemanticDocument
from smart2docx.templates.profile import TemplateProfile


class SemanticModelProvider(ABC):
    """Формирует связные текстовые блоки и сопоставляет их с разделами шаблона.

    Реализация может быть детерминированной либо обращаться к языковой модели.
    Состав аргументов и тип результата от этого не зависят.
    Параметры вёрстки применяет генератор DOCX, а не поставщик текста.
    """

    @abstractmethod
    def render(
        self,
        document: SmartDocument,
        profile: TemplateProfile,
        options: GenerationOptions | None = None,
    ) -> SemanticDocument:
        """Возвращает разделы документа в порядке профиля шаблона."""
