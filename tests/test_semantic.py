"""Проверка детерминированного семантического слоя."""

from smart2docx.schemas.generation import GenerationOptions
from smart2docx.schemas.smart_document import SmartSection
from smart2docx.semantic import MockSemanticProvider
from smart2docx.templates.registry import TemplateRegistry


def _headings(result):
    found = []

    def walk(blocks):
        for block in blocks:
            found.append(block.heading)
            walk(block.children)

    walk(result.blocks)
    return found


def test_mock_provider_is_deterministic(smart_document):
    provider = MockSemanticProvider()
    profile = TemplateRegistry().get("gost_explanatory_note")
    first = provider.render(smart_document, profile)
    second = provider.render(smart_document, profile, GenerationOptions())
    assert first.model_dump() == second.model_dump()


def test_explanatory_note_maps_sections_and_keeps_facts(smart_document):
    result = MockSemanticProvider().render(
        smart_document,
        TemplateRegistry().get("gost_explanatory_note"),
    )
    headings = _headings(result)
    assert headings[0].startswith("1 Общие сведения")
    assert any(item.startswith("3 Описание принятых") for item in headings)
    assert any(item.startswith("3.1 Конструктивные решения") for item in headings)
    assert any(item.startswith("3.1.1 Фундаменты") for item in headings)
    assert any(item.startswith("4 Перечень нормативных") for item in headings)

    text = "\n".join(
        paragraph
        for block in _flat(result.blocks)
        for paragraph in block.paragraphs
    )
    assert "Многоквартирный жилой дом" in text
    assert "безригельного каркаса" in text
    assert "Класс бетона — В30" in text
    assert "СП 63.13330.2018" in text
    assert "1. СП 63.13330.2018" in text

    structural = next(block for block in _flat(result.blocks) if block.code == "KR")
    assert structural.tables[0].rows[0]["mark"] == "КЖ-1"


def test_other_profiles_use_their_own_structure(smart_document):
    provider = MockSemanticProvider()
    registry = TemplateRegistry()
    technical = provider.render(smart_document, registry.get("gost_tech_spec"))
    contract = provider.render(smart_document, registry.get("gost_contract"))
    technical_text = "\n".join(block.heading for block in technical.blocks)
    contract_text = "\n".join(
        paragraph
        for block in contract.blocks
        for paragraph in block.paragraphs
    )
    assert "Назначение и область применения" in technical_text
    assert "Порядок контроля и приёмки" in technical_text
    assert any("Times New Roman" in paragraph for block in technical.blocks for paragraph in block.paragraphs)
    assert "Преамбула" in contract.blocks[0].heading
    assert "ООО «Волжский квартал»" in contract_text
    assert "ООО «КазаньГражданПроект»" in contract_text


def test_unmatched_section_is_appended(smart_document):
    document = smart_document.model_copy(deep=True)
    document.sections.append(
        SmartSection(
            code="CUSTOM",
            title="Особые условия",
            content="Условие сохранено в документе.",
        )
    )
    result = MockSemanticProvider().render(document, TemplateRegistry().get("gost_explanatory_note"))
    headings = _headings(result)
    assert any("Особые условия" in heading for heading in headings)
    assert any(
        "Условие сохранено в документе." in paragraph
        for block in _flat(result.blocks)
        for paragraph in block.paragraphs
    )


def _flat(blocks):
    for block in blocks:
        yield block
        yield from _flat(block.children)
