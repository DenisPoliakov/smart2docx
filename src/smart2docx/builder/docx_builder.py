"""Сборка человекочитаемого документа DOCX."""

from __future__ import annotations

import io

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from docx.text.paragraph import Paragraph

from smart2docx.builder.gost_styles import (
    apply_run_font,
    apply_table_geometry,
    configure_document_defaults,
    configure_page,
    format_body_paragraph,
    format_caption_paragraph,
    format_heading_paragraph,
    shade_header_cell,
)
from smart2docx.schemas.generation import GenerationOptions
from smart2docx.schemas.smart_document import CharacteristicTable
from smart2docx.semantic.model import NarrativeBlock, SemanticDocument
from smart2docx.templates.profile import TemplateProfile

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class DocxBuilder:
    """Собирает DOCX по результату семантического слоя и профилю шаблона.

    Оформление: лист A4, поля 30/15/20/20 мм, Times New Roman 14 пт,
    межстрочный интервал 1,5, абзацный отступ 1,25 см, нумерация страниц,
    таблицы с границами и повторяемой шапкой.
    """

    def build(
        self,
        semantic: SemanticDocument,
        profile: TemplateProfile,
        options: GenerationOptions | None = None,
    ) -> bytes:
        """Возвращает содержимое файла DOCX."""
        options = options or GenerationOptions()
        document = Document()
        configure_document_defaults(document, profile)
        configure_page(
            document.sections[0],
            profile,
            title_page=options.include_title_page,
            cipher=semantic.document_cipher,
        )
        self._table_number = 0
        if options.include_title_page:
            self._add_title_page(document, semantic, profile)
            break_paragraph = document.add_page_break()
            format_body_paragraph(break_paragraph, profile)
            break_paragraph.paragraph_format.first_line_indent = Pt(0)
        for block in semantic.blocks:
            self._add_block(document, block, profile)
        self._set_core_properties(document, semantic, profile)
        buffer = io.BytesIO()
        document.save(buffer)
        return buffer.getvalue()

    def _add_title_page(self, document, semantic: SemanticDocument, profile: TemplateProfile) -> None:
        if semantic.designer:
            self._add_center(document, semantic.designer, profile, bold=True, space_after=12)
        if semantic.document_cipher:
            self._add_center(document, semantic.document_cipher, profile, space_before=12)
        self._add_center(
            document,
            semantic.document_kind.upper(),
            profile,
            bold=True,
            space_before=28,
            space_after=12,
        )
        self._add_center(document, semantic.object_name, profile, space_before=6)
        if semantic.address:
            self._add_center(document, semantic.address, profile, space_before=6)
        if semantic.project_stage:
            self._add_center(document, f"Стадия {semantic.project_stage}", profile, space_before=12)
        if semantic.normative_basis:
            self._add_center(document, ", ".join(semantic.normative_basis), profile, space_before=12)
        if semantic.year is not None:
            self._add_center(document, str(semantic.year), profile, space_before=36)

    def _add_block(self, document, block: NarrativeBlock, profile: TemplateProfile) -> None:
        self._add_heading(document, block.heading, profile, block.level)
        for text in block.paragraphs:
            self._add_body(document, text, profile)
        for table in block.tables:
            self._add_table(document, table, profile)
        for child in block.children:
            self._add_block(document, child, profile)

    def _add_heading(self, document, text: str, profile: TemplateProfile, level: int) -> None:
        paragraph = document.add_paragraph()
        format_heading_paragraph(paragraph, profile, level)
        run = paragraph.add_run(text)
        apply_run_font(run, profile, bold=profile.typography.heading_bold)

    def _add_body(self, document, text: str, profile: TemplateProfile) -> None:
        paragraph = document.add_paragraph()
        format_body_paragraph(paragraph, profile)
        run = paragraph.add_run(text)
        apply_run_font(run, profile)

    def _add_center(
        self,
        document,
        text: str,
        profile: TemplateProfile,
        *,
        bold: bool = False,
        space_before: float = 0,
        space_after: float = 0,
    ) -> None:
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.line_spacing = profile.typography.line_spacing
        paragraph.paragraph_format.first_line_indent = Pt(0)
        paragraph.paragraph_format.space_before = Pt(space_before)
        paragraph.paragraph_format.space_after = Pt(space_after)
        run = paragraph.add_run(text)
        apply_run_font(run, profile, bold=bold)

    def _add_table(self, document, table_data: CharacteristicTable, profile: TemplateProfile) -> None:
        self._table_number += 1
        caption: Paragraph = document.add_paragraph()
        format_caption_paragraph(caption, profile)
        caption_run = caption.add_run(f"Таблица {self._table_number} — {table_data.title}")
        apply_run_font(caption_run, profile)

        column_count = len(table_data.columns)
        table = document.add_table(rows=1, cols=column_count)
        table.style = "Table Grid"
        header = table.rows[0]
        for index, column in enumerate(table_data.columns):
            self._write_cell(header.cells[index], column.title, profile, header=True)
        for row_data in table_data.rows:
            row = table.add_row()
            for index, column in enumerate(table_data.columns):
                self._write_cell(row.cells[index], row_data.get(column.key, ""), profile, header=False)
        apply_table_geometry(table, profile)

    def _write_cell(self, cell, text: str, profile: TemplateProfile, *, header: bool) -> None:
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER if header else WD_ALIGN_PARAGRAPH.LEFT
        paragraph.paragraph_format.line_spacing = profile.typography.line_spacing
        paragraph.paragraph_format.first_line_indent = Pt(0)
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        if paragraph.runs:
            paragraph.runs[0].text = ""
        run = paragraph.add_run(text)
        apply_run_font(run, profile, bold=header)
        if header:
            shade_header_cell(cell)

    def _set_core_properties(self, document, semantic: SemanticDocument, profile: TemplateProfile) -> None:
        properties = document.core_properties
        properties.title = semantic.title
        properties.subject = "; ".join(profile.normative_basis)
        properties.category = profile.document_kind
        properties.keywords = profile.id
        properties.author = semantic.designer or "smart2docx"
        properties.comments = f"Сформировано модулем smart2docx по профилю {profile.id}."
