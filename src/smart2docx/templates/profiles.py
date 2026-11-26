"""Реестр составов документов по ГОСТ.

Общие параметры листа и шрифта заданы в `PageSetup` и `Typography`:
лист A4, поля 30/15/20/20 мм, Times New Roman 14 пт, интервал 1,5,
абзацный отступ 1,25 см.
"""

from __future__ import annotations

from smart2docx.templates.profile import SectionSlot, TemplateProfile

EXPLANATORY_NOTE = TemplateProfile(
    id="gost_explanatory_note",
    title="Пояснительная записка",
    document_kind="Пояснительная записка",
    summary=(
        "Пояснительная записка по ГОСТ Р 21.101-2020 и Положению "
        "о составе разделов проектной документации."
    ),
    normative_basis=(
        "ГОСТ Р 21.101-2020",
        "Постановление Правительства РФ от 16.02.2008 № 87",
    ),
    filename_prefix="pz",
    sections=(
        SectionSlot(
            code="general",
            title="Общие сведения об объекте капитального строительства",
            source_codes=("GENERAL", "META", "COMMON"),
            synthetic="general",
        ),
        SectionSlot(
            code="basis",
            title="Основание для разработки проектной документации",
            source_codes=("BASIS", "OSN", "BASE"),
            synthetic="basis",
        ),
        SectionSlot(
            code="solutions",
            title="Описание принятых технических решений",
            source_codes=("KR", "AR", "IOS", "TX", "POS", "SOLUTIONS", "OVR"),
        ),
        SectionSlot(
            code="norms",
            title="Перечень нормативных документов",
            source_codes=("NORMS", "NORM", "NPA"),
            synthetic="norms",
        ),
    ),
)

TECH_SPEC = TemplateProfile(
    id="gost_tech_spec",
    title="Техническое задание",
    document_kind="Техническое задание",
    summary="Техническое задание на документацию по ГОСТ 2.105-2019.",
    normative_basis=("ГОСТ 2.105-2019",),
    filename_prefix="tz",
    sections=(
        SectionSlot(
            code="purpose",
            title="Назначение и область применения",
            source_codes=("PURPOSE", "GENERAL", "META"),
            synthetic="purpose",
        ),
        SectionSlot(
            code="requirements",
            title="Технические требования",
            source_codes=("REQ", "REQUIREMENTS", "KR", "AR", "IOS", "TX", "SOLUTIONS"),
        ),
        SectionSlot(
            code="docs",
            title="Требования к составу и оформлению документации",
            source_codes=("DOCS", "COMPOSITION"),
            synthetic="docs",
        ),
        SectionSlot(
            code="acceptance",
            title="Порядок контроля и приёмки",
            source_codes=("ACCEPT", "ACCEPTANCE"),
            synthetic="acceptance",
        ),
    ),
)

CONTRACT = TemplateProfile(
    id="gost_contract",
    title="Договор / акт",
    document_kind="Договор",
    summary="Проект договора или акта по ГОСТ Р 7.0.97-2016.",
    normative_basis=("ГОСТ Р 7.0.97-2016",),
    filename_prefix="dogovor",
    sections=(
        SectionSlot(
            code="preamble",
            title="Преамбула",
            source_codes=("PREAMBLE",),
            synthetic="preamble",
        ),
        SectionSlot(
            code="subject",
            title="Предмет договора",
            source_codes=("SUBJECT", "KR", "AR", "IOS", "SOLUTIONS"),
            synthetic="subject",
        ),
        SectionSlot(
            code="obligations",
            title="Обязательства сторон",
            source_codes=("OBLIGATIONS",),
            synthetic="obligations",
        ),
        SectionSlot(
            code="delivery",
            title="Порядок сдачи результатов",
            source_codes=("DELIVERY",),
            synthetic="delivery",
        ),
        SectionSlot(
            code="details",
            title="Реквизиты сторон",
            source_codes=("DETAILS",),
            synthetic="details",
        ),
    ),
)

DEFAULT_PROFILES: tuple[TemplateProfile, ...] = (
    EXPLANATORY_NOTE,
    TECH_SPEC,
    CONTRACT,
)
