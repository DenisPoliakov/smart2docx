"""Общие данные для проверки парсера, текста и сборки DOCX."""

from __future__ import annotations

import io
from pathlib import Path

import anyio
import httpx
import pytest
from docx import Document
from docx.document import Document as DocumentObject
from fastapi import FastAPI

from smart2docx.main import create_app
from smart2docx.schemas.smart_document import SmartDocument

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def sample_payload() -> dict:
    """Возвращает компактный, но содержательный smart-документ."""
    return {
        "document_type": "explanatory_note",
        "metadata": {
            "object_name": "Многоквартирный жилой дом со встроенными помещениями",
            "object_code": "ЖД-17-КН",
            "document_cipher": "012-2026-ПЗ",
            "project_stage": "П",
            "address": "г. Казань, ул. Академика Парина",
            "customer": "ООО «Волжский квартал»",
            "designer": "ООО «КазаньГражданПроект»",
            "chief_engineer": "Петров А.С.",
            "year": 2026,
        },
        "sections": [
            {
                "code": "KR",
                "title": "Конструктивные решения",
                "content": (
                    "Несущий остов принят в виде монолитного безригельного каркаса.\n\n"
                    "Пространственная жёсткость обеспечивается ядрами и дисками перекрытий."
                ),
                "parameters": [
                    {
                        "name": "Конструктивная система",
                        "value": "монолитный железобетонный каркас",
                    },
                    {"name": "Этажность", "value": 17, "unit": "эт."},
                    {"name": "Класс бетона", "value": "В30", "note": "несущие конструкции"},
                ],
                "requirements": [
                    {
                        "code": "СП 63.13330.2018",
                        "source": "СП 63.13330.2018 «Бетонные и железобетонные конструкции»",
                        "text": "Несущие конструкции рассчитаны по предельным состояниям",
                    }
                ],
                "tables": [
                    {
                        "title": "Характеристики колонн",
                        "columns": [
                            {"key": "mark", "title": "Марка"},
                            {"key": "section", "title": "Сечение, мм"},
                            {"key": "concrete", "title": "Бетон"},
                        ],
                        "rows": [
                            {"mark": "КЖ-1", "section": "400х400", "concrete": "В30"},
                            {"mark": "КЖ-2", "section": "500х500", "concrete": "В30", "extra": 1},
                        ],
                    }
                ],
                "subsections": [
                    {
                        "code": "KR.1",
                        "title": "Фундаменты",
                        "content": "Фундамент принят в виде монолитной плиты толщиной 800 мм.",
                        "parameters": [{"name": "Толщина плиты", "value": "800", "unit": "мм"}],
                    }
                ],
            }
        ],
    }


@pytest.fixture
def payload() -> dict:
    return sample_payload()


@pytest.fixture
def smart_document(payload: dict) -> SmartDocument:
    return SmartDocument.model_validate(payload)


@pytest.fixture
def app() -> FastAPI:
    return create_app()


def api_request(app: FastAPI, method: str, url: str, **kwargs) -> httpx.Response:
    """Выполняет запрос к приложению FastAPI через httpx."""

    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.request(method, url, **kwargs)
            await response.aread()
            return response

    return anyio.run(send)


def open_docx(content: bytes) -> DocumentObject:
    return Document(io.BytesIO(content))


def document_text(document: DocumentObject) -> str:
    parts = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                parts.append(cell.text)
    return "\n".join(parts)


def assert_length_mm(length, expected_mm: float, tolerance: float = 0.2) -> None:
    """Сравнивает длину с миллиметрами с допуском на округление до твипов."""
    assert length is not None
    assert abs(length.mm - expected_mm) <= tolerance
