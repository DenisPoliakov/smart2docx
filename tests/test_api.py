"""Проверка HTTP-интерфейса генерации документов."""

import json

from smart2docx import __version__
from smart2docx.builder.docx_builder import DOCX_MEDIA_TYPE
from smart2docx.main import content_disposition
from tests.conftest import api_request, document_text, open_docx


def test_health(app):
    response = api_request(app, "GET", "/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "smart2docx",
        "version": __version__,
    }


def test_list_templates(app):
    response = api_request(app, "GET", "/api/v1/templates")
    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == [
        "gost_contract",
        "gost_explanatory_note",
        "gost_tech_spec",
    ]
    explanatory = next(item for item in payload if item["id"] == "gost_explanatory_note")
    assert "ГОСТ Р 21.101-2020" in explanatory["normative_basis"]
    assert explanatory["sections"]
    assert explanatory["document_kind"] == "Пояснительная записка"


def test_generate_from_json_returns_docx(app, payload):
    response = api_request(
        app,
        "POST",
        "/api/v1/generate",
        json={"template_id": "gost_explanatory_note", "document": payload},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == DOCX_MEDIA_TYPE
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert "filename*=UTF-8''" in disposition
    assert ".docx" in disposition
    assert response.content.startswith(b"PK")
    text = document_text(open_docx(response.content))
    assert "КЖ-1" in text
    assert "Конструктивные решения" in text


def test_generate_from_raw_document_query(app, payload):
    response = api_request(
        app,
        "POST",
        "/api/v1/generate",
        params={"template_id": "gost_tech_spec"},
        json=payload,
    )
    assert response.status_code == 200
    text = document_text(open_docx(response.content))
    assert "Техническое задание".upper() in text
    assert "Технические требования" in text


def test_generate_from_multipart_json_and_xml(app, payload):
    json_response = api_request(
        app,
        "POST",
        "/api/v1/generate",
        data={"template_id": "gost_contract", "include_title_page": "false"},
        files={"file": ("note.json", json.dumps(payload, ensure_ascii=False).encode(), "application/json")},
    )
    assert json_response.status_code == 200
    contract = open_docx(json_response.content)
    assert contract.paragraphs[0].text.startswith("1 ")
    assert "Преамбула" in contract.paragraphs[0].text

    xml = """
    <smartDocument>
      <metadata><objectName>Детский сад</objectName></metadata>
      <sections>
        <section code="AR" title="Архитектурные решения">
          <content>Здание трёхэтажное.</content>
        </section>
      </sections>
    </smartDocument>
    """.encode()
    xml_response = api_request(
        app,
        "POST",
        "/api/v1/generate",
        data={"template_id": "gost_explanatory_note"},
        files={"file": ("note.xml", xml, "application/xml")},
    )
    assert xml_response.status_code == 200
    assert "Детский сад" in document_text(open_docx(xml_response.content))
    assert "Архитектурные решения" in document_text(open_docx(xml_response.content))


def test_generate_camel_case_json(app):
    response = api_request(
        app,
        "POST",
        "/api/v1/generate",
        json={
            "templateId": "gost_explanatory_note",
            "document": {
                "metadata": {"objectName": "Склад"},
                "sections": [{"code": "KR", "title": "Каркас", "content": "Рамный каркас."}],
            },
            "options": {"includeTitlePage": False},
        },
    )
    assert response.status_code == 200
    assert open_docx(response.content).paragraphs[0].text.startswith("1 ")


def test_unknown_template_and_invalid_body(app, payload):
    missing = api_request(
        app,
        "POST",
        "/api/v1/generate",
        json={"template_id": "missing", "document": payload},
    )
    assert missing.status_code == 404
    assert "missing" in missing.json()["detail"]

    invalid = api_request(
        app,
        "POST",
        "/api/v1/generate",
        json={"template_id": "gost_explanatory_note", "document": {"metadata": {}}},
    )
    assert invalid.status_code == 422

    empty = api_request(
        app,
        "POST",
        "/api/v1/generate",
        content=b"",
        headers={"content-type": "application/json"},
    )
    assert empty.status_code == 422

    unsupported = api_request(
        app,
        "POST",
        "/api/v1/generate",
        content=b"text",
        headers={"content-type": "text/plain"},
    )
    assert unsupported.status_code == 415


def test_multipart_without_file(app):
    response = api_request(
        app,
        "POST",
        "/api/v1/generate",
        files={"template_id": (None, "gost_explanatory_note")},
    )
    assert response.status_code == 422


def test_content_disposition_ascii_and_unicode():
    ascii_header = content_disposition("pz_012.docx")
    assert 'filename="pz_012.docx"' in ascii_header
    unicode_header = content_disposition("pz_012-2026-ПЗ.docx")
    assert 'filename="document.docx"' in unicode_header
    assert "filename*=UTF-8''" in unicode_header
    assert "%D0%9F" in unicode_header
