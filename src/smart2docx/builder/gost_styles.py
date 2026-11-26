"""Низкоуровневое оформление DOCX по принятым параметрам ГОСТ."""

from __future__ import annotations

from docx.document import Document as DocumentObject
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Emu, Mm, Pt
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from smart2docx.templates.profile import TemplateProfile

_BORDER_EDGES = ("top", "left", "bottom", "right", "insideH", "insideV")


def configure_document_defaults(document: DocumentObject, profile: TemplateProfile) -> None:
    """Задаёт стиль Normal: шрифт, кегль и межстрочный интервал."""
    style = document.styles["Normal"]
    font = profile.typography
    style.font.name = font.font_name
    style.font.size = Pt(font.font_size_pt)
    style.font.bold = False
    _set_complex_script_font(style.element.get_or_add_rPr(), font.font_name)
    paragraph_format = style.paragraph_format
    paragraph_format.line_spacing = font.line_spacing
    paragraph_format.space_before = Pt(0)
    paragraph_format.space_after = Pt(0)
    paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    enable_field_update(document)


def configure_page(section, profile: TemplateProfile, *, title_page: bool, cipher: str | None) -> None:
    """Настраивает лист A4, поля, колонтитулы и нумерацию страниц."""
    page = profile.page
    section.page_width = Mm(page.width_mm)
    section.page_height = Mm(page.height_mm)
    section.left_margin = Mm(page.margin_left_mm)
    section.right_margin = Mm(page.margin_right_mm)
    section.top_margin = Mm(page.margin_top_mm)
    section.bottom_margin = Mm(page.margin_bottom_mm)
    section.header_distance = Mm(10)
    section.footer_distance = Mm(10)
    section.different_first_page_header_footer = title_page

    header = section.header
    header.is_linked_to_previous = False
    header_paragraph = header.paragraphs[0]
    _clear_paragraph(header_paragraph)
    format_auxiliary_paragraph(header_paragraph, profile, align=WD_ALIGN_PARAGRAPH.RIGHT)
    if cipher:
        run = header_paragraph.add_run(cipher)
        apply_run_font(run, profile)

    footer = section.footer
    footer.is_linked_to_previous = False
    footer_paragraph = footer.paragraphs[0]
    _clear_paragraph(footer_paragraph)
    format_auxiliary_paragraph(footer_paragraph, profile, align=WD_ALIGN_PARAGRAPH.CENTER)
    page_run = add_page_number_field(footer_paragraph)
    apply_run_font(page_run, profile)

    if not title_page:
        return
    first_header = section.first_page_header
    first_header.is_linked_to_previous = False
    _clear_paragraph(first_header.paragraphs[0])
    first_footer = section.first_page_footer
    first_footer.is_linked_to_previous = False
    _clear_paragraph(first_footer.paragraphs[0])


def enable_field_update(document: DocumentObject) -> None:
    """Просит редактор обновить поля, включая номер страницы, при открытии."""
    settings = document.settings.element
    node = settings.find(qn("w:updateFields"))
    if node is None:
        node = OxmlElement("w:updateFields")
        settings.append(node)
    node.set(qn("w:val"), "true")


def apply_run_font(
    run: Run,
    profile: TemplateProfile,
    *,
    bold: bool = False,
    size_pt: float | None = None,
) -> None:
    """Назначает гарнитуру Times New Roman всем группам письма."""
    font_name = profile.typography.font_name
    run.font.name = font_name
    run.font.size = Pt(size_pt if size_pt is not None else profile.typography.font_size_pt)
    run.bold = bold
    run.italic = False
    _set_complex_script_font(run._element.get_or_add_rPr(), font_name)


def format_body_paragraph(paragraph: Paragraph, profile: TemplateProfile) -> None:
    """Форматирует абзац основного текста: ширина, интервал 1,5, отступ 1,25 см."""
    font = profile.typography
    paragraph_format = paragraph.paragraph_format
    paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph_format.line_spacing = font.line_spacing
    paragraph_format.first_line_indent = Cm(font.first_line_indent_cm)
    paragraph_format.space_before = Pt(0)
    paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.widow_control = True


def format_heading_paragraph(paragraph: Paragraph, profile: TemplateProfile, level: int) -> None:
    """Форматирует заголовок раздела без точки, подчёркивания и абзацного отступа."""
    font = profile.typography
    paragraph_format = paragraph.paragraph_format
    paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER if level <= 1 else WD_ALIGN_PARAGRAPH.LEFT
    paragraph_format.line_spacing = font.line_spacing
    paragraph_format.first_line_indent = Cm(0)
    paragraph_format.space_before = Pt(12)
    paragraph_format.space_after = Pt(6)
    paragraph_format.keep_with_next = True


def format_auxiliary_paragraph(paragraph: Paragraph, profile: TemplateProfile, *, align) -> None:
    """Форматирует строку титульного листа, колонтитула или подписи таблицы."""
    paragraph_format = paragraph.paragraph_format
    paragraph_format.alignment = align
    paragraph_format.line_spacing = profile.typography.line_spacing
    paragraph_format.first_line_indent = Cm(0)
    paragraph_format.space_before = Pt(0)
    paragraph_format.space_after = Pt(0)


def format_caption_paragraph(paragraph: Paragraph, profile: TemplateProfile) -> None:
    """Форматирует подпись таблицы по ГОСТ 2.105: «Таблица N — название»."""
    format_auxiliary_paragraph(paragraph, profile, align=WD_ALIGN_PARAGRAPH.LEFT)
    paragraph.paragraph_format.space_before = Pt(12)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.keep_with_next = True


def add_page_number_field(paragraph: Paragraph) -> Run:
    """Вставляет поле PAGE в указанный абзац."""
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    cached = OxmlElement("w:t")
    cached.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instruction)
    run._r.append(separate)
    run._r.append(cached)
    run._r.append(end)
    return run


def apply_table_geometry(table: Table, profile: TemplateProfile) -> None:
    """Задаёт границы, ширину по текстовому полю и повтор шапки на каждой странице."""
    _set_table_borders(table)
    _set_table_width(table, profile)
    if table.rows:
        _mark_header_row(table.rows[0])


def shade_header_cell(cell) -> None:
    """Заливает ячейку шапки светло-серым цветом."""
    properties = cell._tc.get_or_add_tcPr()
    shading = properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        properties.append(shading)
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), "D9D9D9")
    alignment = properties.find(qn("w:vAlign"))
    if alignment is None:
        alignment = OxmlElement("w:vAlign")
        properties.append(alignment)
    alignment.set(qn("w:val"), "center")


def _set_complex_script_font(run_properties, font_name: str) -> None:
    fonts = run_properties.get_or_add_rFonts()
    fonts.set(qn("w:cs"), font_name)
    fonts.set(qn("w:eastAsia"), font_name)
    language = run_properties.find(qn("w:lang"))
    if language is None:
        language = OxmlElement("w:lang")
        run_properties.append(language)
    language.set(qn("w:val"), "ru-RU")
    language.set(qn("w:eastAsia"), "ru-RU")


def _set_table_borders(table: Table) -> None:
    properties = table._tbl.tblPr
    borders = properties.find(qn("w:tblBorders"))
    if borders is not None:
        properties.remove(borders)
    borders = OxmlElement("w:tblBorders")
    for edge in _BORDER_EDGES:
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "8")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "000000")
        borders.append(element)
    layout = properties.find(qn("w:tblLayout"))
    if layout is not None:
        layout.addprevious(borders)
    else:
        properties.append(borders)


def _set_table_width(table: Table, profile: TemplateProfile) -> None:
    width = Mm(profile.page.content_width_mm)
    properties = table._tbl.tblPr
    table_width = properties.find(qn("w:tblW"))
    if table_width is None:
        table_width = OxmlElement("w:tblW")
        properties.append(table_width)
    table_width.set(qn("w:type"), "dxa")
    table_width.set(qn("w:w"), str(int(width.twips)))
    table.autofit = False
    column_count = len(table.columns)
    if column_count == 0:
        return
    column_width = Emu(int(width) // column_count)
    for column in table.columns:
        column.width = column_width


def _mark_header_row(row) -> None:
    properties = row._tr.get_or_add_trPr()
    marker = properties.find(qn("w:tblHeader"))
    if marker is None:
        marker = OxmlElement("w:tblHeader")
        properties.append(marker)
    marker.set(qn("w:val"), "true")


def _clear_paragraph(paragraph: Paragraph) -> None:
    element = paragraph._p
    for child in list(element):
        if child.tag != qn("w:pPr"):
            element.remove(child)
