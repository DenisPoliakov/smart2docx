"""Параметры профиля шаблона, не зависящие от конкретного документа."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PageSetup:
    """Геометрия листа.

    Поля 30/15/20/20 мм — левое, правое, верхнее и нижнее.
    Левое поле увеличено под переплёт текстового документа.
    """

    width_mm: float = 210.0
    height_mm: float = 297.0
    margin_left_mm: float = 30.0
    margin_right_mm: float = 15.0
    margin_top_mm: float = 20.0
    margin_bottom_mm: float = 20.0

    @property
    def content_width_mm(self) -> float:
        """Ширина текстового поля, мм."""
        return self.width_mm - self.margin_left_mm - self.margin_right_mm


@dataclass(frozen=True)
class Typography:
    """Параметры шрифта и абзаца основного текста."""

    font_name: str = "Times New Roman"
    font_size_pt: float = 14.0
    line_spacing: float = 1.5
    first_line_indent_cm: float = 1.25
    heading_bold: bool = True


@dataclass(frozen=True)
class SectionSlot:
    """Раздел шаблона и коды smart-документа, которые в него попадают."""

    code: str
    title: str
    source_codes: tuple[str, ...] = ()
    synthetic: str | None = None


@dataclass(frozen=True)
class TemplateProfile:
    """Профиль оформления и состав разделов документа ГОСТ."""

    id: str
    title: str
    document_kind: str
    summary: str
    normative_basis: tuple[str, ...]
    filename_prefix: str
    sections: tuple[SectionSlot, ...]
    page: PageSetup = field(default_factory=PageSetup)
    typography: Typography = field(default_factory=Typography)
