"""Проверка оформления DOCX по принятым параметрам ГОСТ."""

import io
import zipfile

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

from smart2docx.schemas.generation import GenerationOptions
from smart2docx.service import generate_document
from tests.conftest import assert_length_mm, document_text, open_docx

TEMPLATE_IDS = ("gost_explanatory_note", "gost_tech_spec", "gost_contract")


def test_examples_of_all_templates_are_valid_docx(smart_document):
    for template_id in TEMPLATE_IDS:
        generated = generate_document(smart_document, template_id)
        assert generated.filename.endswith(".docx")
        assert generated.content.startswith(b"PK")
        with zipfile.ZipFile(io.BytesIO(generated.content)) as archive:
            assert archive.testzip() is None
            assert "word/document.xml" in archive.namelist()
        text = document_text(open_docx(generated.content))
        assert "Многоквартирный жилой дом" in text


def test_gost_page_and_paragraph_styles(smart_document):
    generated = generate_document(smart_document, "gost_explanatory_note")
    document = open_docx(generated.content)
    section = document.sections[0]

    assert_length_mm(section.page_width, 210)
    assert_length_mm(section.page_height, 297)
    assert_length_mm(section.left_margin, 30)
    assert_length_mm(section.right_margin, 15)
    assert_length_mm(section.top_margin, 20)
    assert_length_mm(section.bottom_margin, 20)
    assert section.page_height > section.page_width

    normal = document.styles["Normal"]
    assert normal.font.name == "Times New Roman"
    assert normal.font.size == Pt(14)
    assert normal.paragraph_format.line_spacing == 1.5

    heading = next(paragraph for paragraph in document.paragraphs if paragraph.text.startswith("1 Общие сведения"))
    assert heading.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert heading.runs[0].bold is True
    assert heading.runs[0].font.name == "Times New Roman"
    assert heading.runs[0].font.size == Pt(14)
    heading_indent = heading.paragraph_format.first_line_indent
    assert heading_indent in (None, 0) or abs(heading_indent.mm) <= 0.05

    body = next(
        paragraph
        for paragraph in document.paragraphs
        if paragraph.text.startswith("Приняты следующие характеристики")
    )
    assert body.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY
    assert body.paragraph_format.line_spacing == 1.5
    assert_length_mm(body.paragraph_format.first_line_indent, 12.5)
    assert body.runs[0].font.name == "Times New Roman"
    assert body.runs[0].font.size == Pt(14)
    assert body.runs[0].bold is False

    nested = next(paragraph for paragraph in document.paragraphs if paragraph.text.startswith("3.1.1 "))
    assert nested.alignment == WD_ALIGN_PARAGRAPH.LEFT


def test_tables_borders_header_and_values(smart_document):
    document = open_docx(generate_document(smart_document, "gost_explanatory_note").content)
    assert any(paragraph.text == "Таблица 1 — Характеристики колонн" for paragraph in document.paragraphs)
    table = document.tables[0]
    assert table.rows[0].cells[0].text == "Марка"
    assert table.rows[0].cells[1].text == "Сечение, мм"
    assert table.rows[1].cells[0].text == "КЖ-1"
    assert table.rows[2].cells[2].text == "В30"

    header_run = table.rows[0].cells[0].paragraphs[0].runs[0]
    assert header_run.bold is True
    assert header_run.font.name == "Times New Roman"
    assert header_run.font.size == Pt(14)
    assert "D9D9D9" in table.rows[0].cells[0]._tc.xml

    xml = table._tbl.xml
    assert "tblBorders" in xml
    assert "tblHeader" in xml
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        assert f"w:{edge}" in xml

    width = table._tbl.tblPr.find(qn("w:tblW"))
    width_mm = int(width.get(qn("w:w"))) * 25.4 / 1440
    assert abs(width_mm - 165) <= 0.5


def test_page_number_and_title_page(smart_document):
    generated = generate_document(smart_document, "gost_explanatory_note")
    document = open_docx(generated.content)
    section = document.sections[0]
    assert section.different_first_page_header_footer is True
    assert "PAGE" in section.footer._element.xml
    assert "PAGE" not in section.first_page_footer._element.xml
    assert section.header.paragraphs[0].text == "012-2026-ПЗ"
    assert section.first_page_header.paragraphs[0].text == ""
    assert "ПОЯСНИТЕЛЬНАЯ ЗАПИСКА" in document.paragraphs[2].text
    assert 'w:type="page"' in document.element.xml

    plain = generate_document(
        smart_document,
        "gost_explanatory_note",
        options=GenerationOptions(include_title_page=False),
    )
    plain_document = open_docx(plain.content)
    assert plain_document.sections[0].different_first_page_header_footer is False
    assert "PAGE" in plain_document.sections[0].footer._element.xml
    assert 'w:type="page"' not in plain_document.element.xml
    assert plain_document.paragraphs[0].text.startswith("1 ")
