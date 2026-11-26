"""Сквозная проверка примеров из каталога examples."""

import io
import zipfile

import pytest

from smart2docx.parsers import parse_document
from smart2docx.service import generate_document
from tests.conftest import EXAMPLES, assert_length_mm, document_text, open_docx


@pytest.mark.parametrize(
    ("filename", "marker"),
    [
        ("structural_solutions.json", "безригельного каркаса"),
        ("architectural_solutions.xml", "дошкольного образовательного учреждения"),
    ],
)
def test_example_builds_explanatory_note(filename, marker):
    source = (EXAMPLES / filename).read_bytes()
    document = parse_document(source, filename=filename)
    generated = generate_document(document, "gost_explanatory_note")

    assert generated.filename.endswith(".docx")
    assert generated.content.startswith(b"PK")
    with zipfile.ZipFile(io.BytesIO(generated.content)) as archive:
        assert archive.testzip() is None
        assert "word/document.xml" in archive.namelist()

    word = open_docx(generated.content)
    section = word.sections[0]
    assert_length_mm(section.page_width, 210)
    assert_length_mm(section.page_height, 297)
    assert_length_mm(section.left_margin, 30)
    assert_length_mm(section.right_margin, 15)
    assert_length_mm(section.top_margin, 20)
    assert_length_mm(section.bottom_margin, 20)

    text = document_text(word)
    assert marker in text
    assert word.tables
    assert "PAGE" in section.footer._element.xml


def test_json_example_accepts_every_builtin_template():
    source = (EXAMPLES / "structural_solutions.json").read_text(encoding="utf-8")
    document = parse_document(source, filename="structural_solutions.json")
    for template_id in ("gost_explanatory_note", "gost_tech_spec", "gost_contract"):
        generated = generate_document(document, template_id)
        text = document_text(open_docx(generated.content))
        assert "В30" in text
        assert "Пилоны 1–10 этажей" in text
        assert "500х500" in text
