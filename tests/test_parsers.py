"""Проверка разбора JSON и XML в модель SmartDocument."""

import json

import pytest

from smart2docx.errors import DocumentParseError
from smart2docx.parsers import parse_document, parse_json, parse_xml

MINIMAL_XML = """<?xml version="1.0" encoding="UTF-8"?>
<smartDocument documentType="explanatory_note">
  <metadata>
    <objectName>Объект</objectName>
    <year>2026</year>
  </metadata>
  <sections>
    <section code="KR" title="Конструктивные решения">
      <content>Каркас монолитный.</content>
      <parameters>
        <parameter name="Этажность" value="17" unit="эт."/>
      </parameters>
      <requirements>
        <requirement code="СП 63.13330.2018" source="СП 63.13330.2018">
          Конструкции рассчитаны по предельным состояниям.
        </requirement>
      </requirements>
      <tables>
        <table title="Колонны">
          <columns>
            <column key="mark" title="Марка"/>
          </columns>
          <rows>
            <row>
              <cell key="mark">КЖ-1</cell>
            </row>
          </rows>
        </table>
      </tables>
      <subsections>
        <section code="KR.1" title="Фундаменты">
          <content>Плита.</content>
        </section>
      </subsections>
    </section>
  </sections>
</smartDocument>
"""


def test_parse_json_payload(payload):
    document = parse_json(json.dumps(payload, ensure_ascii=False))
    assert document.metadata.object_name.startswith("Многоквартирный")
    assert document.metadata.year == 2026
    section = document.sections[0]
    assert section.code == "KR"
    assert section.parameters[1].value == "17"
    assert section.parameters[1].unit == "эт."
    assert section.tables[0].rows[0]["mark"] == "КЖ-1"
    assert section.tables[0].rows[1]["extra"] == "1"
    assert section.subsections[0].title == "Фундаменты"


def test_parse_json_accepts_camel_case():
    document = parse_json(
        {
            "documentType": "explanatory_note",
            "metadata": {"objectName": "Объект", "projectStage": "П"},
            "sections": [{"code": "KR", "title": "Раздел", "content": "Текст."}],
            "unknown": {"ignored": True},
        }
    )
    assert document.metadata.object_name == "Объект"
    assert document.metadata.project_stage == "П"
    assert document.sections[0].content == "Текст."


def test_json_and_xml_minimal_models_match():
    json_document = parse_json(
        {
            "document_type": "explanatory_note",
            "metadata": {"object_name": "Объект", "year": 2026},
            "sections": [
                {
                    "code": "KR",
                    "title": "Конструктивные решения",
                    "content": "Каркас монолитный.",
                    "parameters": [{"name": "Этажность", "value": "17", "unit": "эт."}],
                    "requirements": [
                        {
                            "code": "СП 63.13330.2018",
                            "source": "СП 63.13330.2018",
                            "text": "Конструкции рассчитаны по предельным состояниям.",
                        }
                    ],
                    "tables": [
                        {
                            "title": "Колонны",
                            "columns": [{"key": "mark", "title": "Марка"}],
                            "rows": [{"mark": "КЖ-1"}],
                        }
                    ],
                    "subsections": [
                        {"code": "KR.1", "title": "Фундаменты", "content": "Плита."}
                    ],
                }
            ],
        }
    )
    xml_document = parse_xml(MINIMAL_XML)
    assert xml_document.model_dump() == json_document.model_dump()


def test_xml_namespace_and_attribute_row():
    source = """
    <s:smartDocument xmlns:s="urn:smart2docx">
      <s:metadata>
        <s:objectName>Школа</s:objectName>
      </s:metadata>
      <s:sections>
        <s:section code="AR" title="Архитектурные решения">
          <s:tables>
            <s:table title="Помещения">
              <s:columns>
                <s:column key="name" title="Наименование"/>
              </s:columns>
              <s:rows>
                <s:row name="Класс"/>
              </s:rows>
            </s:table>
          </s:tables>
        </s:section>
      </s:sections>
    </s:smartDocument>
    """
    document = parse_document(source, filename="school.xml")
    assert document.metadata.object_name == "Школа"
    assert document.sections[0].tables[0].rows[0]["name"] == "Класс"


def test_detects_format_by_content():
    document = parse_document('{"metadata": {"object_name": "Цех"}, "sections": [{"code": "KR", "title": "Раздел"}]}')
    assert document.metadata.object_name == "Цех"


@pytest.mark.parametrize(
    "payload",
    ["{", "<smartDocument>", "<root/>", "просто текст", b"\xff\xfe"],
)
def test_malformed_input_is_rejected(payload):
    with pytest.raises(DocumentParseError):
        parse_document(payload)


def test_schema_rejects_empty_sections_and_year():
    with pytest.raises(DocumentParseError):
        parse_json({"metadata": {"object_name": "Объект"}, "sections": []})
    with pytest.raises(DocumentParseError, match="1900"):
        parse_json(
            {
                "metadata": {"object_name": "Объект", "year": 1800},
                "sections": [{"code": "KR", "title": "Раздел"}],
            }
        )


def test_duplicate_table_keys_are_rejected():
    with pytest.raises(DocumentParseError):
        parse_json(
            {
                "metadata": {"object_name": "Объект"},
                "sections": [
                    {
                        "code": "KR",
                        "title": "Раздел",
                        "tables": [
                            {
                                "title": "Таблица",
                                "columns": [
                                    {"key": "mark", "title": "Марка"},
                                    {"key": "mark", "title": "Повтор"},
                                ],
                                "rows": [],
                            }
                        ],
                    }
                ],
            }
        )
