"""Детерминированное формирование текста без внешнего API."""

from __future__ import annotations

from collections.abc import Callable

from smart2docx.schemas.generation import GenerationOptions
from smart2docx.schemas.smart_document import Parameter, Requirement, SmartDocument, SmartSection
from smart2docx.semantic.model import NarrativeBlock, SemanticDocument
from smart2docx.semantic.provider import SemanticModelProvider
from smart2docx.templates.profile import SectionSlot, TemplateProfile

SyntheticBuilder = Callable[[SmartDocument], list[str]]


class MockSemanticProvider(SemanticModelProvider):
    """Собирает инженерный текст из реквизитов, параметров, требований и таблиц.

    Одинаковые входные данные всегда дают одинаковый результат.
    Сетевые вызовы и ключи доступа не используются.
    Разделы, не попавшие ни в один слот шаблона, добавляются в конец документа.
    """

    def render(
        self,
        document: SmartDocument,
        profile: TemplateProfile,
        options: GenerationOptions | None = None,
    ) -> SemanticDocument:
        del options
        consumed: set[int] = set()
        blocks: list[NarrativeBlock] = []
        for slot in profile.sections:
            block = _render_slot(document, slot, consumed)
            if block is not None:
                blocks.append(block)
        for index, section in enumerate(document.sections):
            if index in consumed:
                continue
            extra = _block_from_section(section)
            if not _is_empty(extra):
                blocks.append(extra)
        metadata = document.metadata
        return SemanticDocument(
            template_id=profile.id,
            title=f"{profile.document_kind}. {metadata.object_name}",
            document_kind=profile.document_kind,
            object_name=metadata.object_name,
            document_cipher=metadata.document_cipher,
            designer=metadata.designer,
            customer=metadata.customer,
            address=metadata.address,
            project_stage=metadata.project_stage,
            year=metadata.year,
            normative_basis=list(profile.normative_basis),
            blocks=_number_blocks(blocks),
        )


def _render_slot(
    document: SmartDocument,
    slot: SectionSlot,
    consumed: set[int],
) -> NarrativeBlock | None:
    matched = _take_sections(document, slot, consumed)
    paragraphs: list[str] = []
    if slot.synthetic:
        builder = _SYNTHETIC.get(slot.synthetic)
        if builder is not None:
            paragraphs.extend(builder(document))
    tables = []
    children: list[NarrativeBlock] = []
    if len(matched) == 1 and _same_title(matched[0].title, slot.title):
        nested = _block_from_section(matched[0])
        paragraphs.extend(nested.paragraphs)
        tables.extend(nested.tables)
        children.extend(nested.children)
    else:
        for section in matched:
            child = _block_from_section(section)
            if not _is_empty(child):
                children.append(child)
    if not paragraphs and not tables and not children:
        return None
    return NarrativeBlock(
        code=slot.code,
        heading=_clean_heading(slot.title),
        level=1,
        paragraphs=paragraphs,
        tables=tables,
        children=children,
    )


def _take_sections(
    document: SmartDocument,
    slot: SectionSlot,
    consumed: set[int],
) -> list[SmartSection]:
    codes = {code.casefold() for code in slot.source_codes}
    matched: list[SmartSection] = []
    if not codes:
        return matched
    for index, section in enumerate(document.sections):
        if index in consumed:
            continue
        if section.code.casefold() in codes:
            consumed.add(index)
            matched.append(section)
    return matched


def _block_from_section(section: SmartSection) -> NarrativeBlock:
    children = []
    for child in section.subsections:
        block = _block_from_section(child)
        if not _is_empty(block):
            children.append(block)
    return NarrativeBlock(
        code=section.code,
        heading=_clean_heading(section.title),
        level=1,
        paragraphs=_section_paragraphs(section),
        tables=list(section.tables),
        children=children,
    )


def _section_paragraphs(section: SmartSection) -> list[str]:
    paragraphs = _split_prose(section.content)
    parameters = _format_parameters(section.parameters)
    if parameters:
        paragraphs.append(parameters)
    paragraphs.extend(_format_requirement(item) for item in section.requirements)
    return paragraphs


def _is_empty(block: NarrativeBlock) -> bool:
    return not block.paragraphs and not block.tables and not block.children


def _same_title(left: str, right: str) -> bool:
    return _clean_heading(left).casefold() == _clean_heading(right).casefold()


def _clean_heading(title: str) -> str:
    return " ".join(title.split()).rstrip(".")


def _number_blocks(blocks: list[NarrativeBlock], prefix: tuple[int, ...] = ()) -> list[NarrativeBlock]:
    numbered: list[NarrativeBlock] = []
    for index, block in enumerate(blocks, start=1):
        path = prefix + (index,)
        number = ".".join(str(item) for item in path)
        numbered.append(
            block.model_copy(
                update={
                    "heading": f"{number} {_clean_heading(block.heading)}",
                    "level": len(path),
                    "children": _number_blocks(block.children, path),
                }
            )
        )
    return numbered


def _split_prose(content: str | None) -> list[str]:
    if content is None or not content.strip():
        return []
    paragraphs: list[str] = []
    for block in content.strip().split("\n\n"):
        text = " ".join(block.split())
        if text:
            paragraphs.append(text)
    return paragraphs


def _format_parameters(parameters: list[Parameter]) -> str | None:
    if not parameters:
        return None
    chunks: list[str] = []
    for parameter in parameters:
        unit = f" {parameter.unit}" if parameter.unit else ""
        chunk = f"{parameter.name} — {parameter.value}{unit}"
        if parameter.note:
            chunk += f" ({parameter.note})"
        chunks.append(chunk)
    return "Приняты следующие характеристики: " + "; ".join(chunks) + "."


def _format_requirement(requirement: Requirement) -> str:
    text = _ensure_sentence(requirement.text.strip())
    label = _requirement_label(requirement)
    if not label:
        return text
    return f"Согласно {label}: {_decapitalize(text)}"


def _requirement_label(requirement: Requirement) -> str | None:
    code = (requirement.code or "").strip()
    source = (requirement.source or "").strip()
    if source and code and code in source:
        return source
    if code and source:
        return f"{code} ({source})"
    return source or code or None


def _ensure_sentence(text: str) -> str:
    if text and text[-1] not in ".!?":
        return text + "."
    return text


def _decapitalize(text: str) -> str:
    if len(text) >= 2 and text[0].isupper() and text[1].islower():
        return text[0].lower() + text[1:]
    return text


def _party(name: str | None, fallback: str) -> str:
    return name.strip() if name else fallback


def _general_paragraphs(document: SmartDocument) -> list[str]:
    meta = document.metadata
    sentences = [f"Объект капитального строительства — «{meta.object_name}»."]
    if meta.address:
        sentences.append(f"Адрес объекта: {meta.address}.")
    if meta.customer:
        sentences.append(f"Заказчик: {meta.customer}.")
    if meta.designer:
        sentences.append(f"Генеральный проектировщик: {meta.designer}.")
    if meta.chief_engineer:
        sentences.append(f"Главный инженер проекта: {meta.chief_engineer}.")
    if meta.object_code:
        sentences.append(f"Код объекта: {meta.object_code}.")
    return [" ".join(sentences)]


def _basis_paragraphs(document: SmartDocument) -> list[str]:
    meta = document.metadata
    sentences = []
    if meta.project_stage:
        sentences.append(f"Документация разработана на стадии «{meta.project_stage}».")
    else:
        sentences.append("Стадия проектирования во входных данных не указана.")
    if meta.document_cipher:
        sentences.append(f"Обозначение документа — {meta.document_cipher}.")
    if meta.year:
        sentences.append(f"Год разработки — {meta.year}.")
    sentences.append(
        "Исходные данные приняты по заданию заказчика и переданы в составе машиночитаемого описания объекта."
    )
    return [" ".join(sentences)]


def _norms_paragraphs(document: SmartDocument) -> list[str]:
    references = _collect_references(document)
    if not references:
        return ["Перечень нормативных документов во входных данных не приведён."]
    paragraphs = ["При подготовке документа учтены следующие нормативные источники:"]
    for index, reference in enumerate(references, start=1):
        paragraphs.append(f"{index}. {reference.rstrip('.')}.")
    return paragraphs


def _collect_references(document: SmartDocument) -> list[str]:
    references: list[str] = []
    seen: set[str] = set()
    for section in document.walk_sections():
        for requirement in section.requirements:
            label = (requirement.source or requirement.code or "").strip()
            if not label or label in seen:
                continue
            seen.add(label)
            references.append(label)
    return references


def _purpose_paragraphs(document: SmartDocument) -> list[str]:
    meta = document.metadata
    sentences = [
        "Настоящее техническое задание определяет состав требований к объекту "
        f"«{meta.object_name}» и к разрабатываемой по нему документации."
    ]
    if meta.address:
        sentences.append(f"Объект расположен по адресу: {meta.address}.")
    if meta.customer:
        sentences.append(f"Заказчик работ — {meta.customer}.")
    return [" ".join(sentences)]


def _docs_paragraphs(document: SmartDocument) -> list[str]:
    del document
    return [
        "В состав разрабатываемой документации включаются текстовые и графические материалы, "
        "предусмотренные заданием заказчика и применимыми стандартами.",
        "Текстовая часть оформляется на листах формата A4. Основной шрифт — Times New Roman, "
        "кегль 14 пт, межстрочный интервал 1,5, абзацный отступ 1,25 см. "
        "Поля листа: левое 30 мм, правое 15 мм, верхнее и нижнее по 20 мм.",
    ]


def _acceptance_paragraphs(document: SmartDocument) -> list[str]:
    del document
    return [
        "Контроль документации выполняется на соответствие настоящему техническому заданию, "
        "заданию заказчика и указанным нормативным документам.",
        "Приёмка производится заказчиком по комплектности разделов и согласованности "
        "числовых характеристик с исходными данными.",
    ]


def _preamble_paragraphs(document: SmartDocument) -> list[str]:
    meta = document.metadata
    designer = _party(meta.designer, "Исполнитель")
    customer = _party(meta.customer, "Заказчик")
    return [
        f"Исполнитель — {designer}. Заказчик — {customer}. "
        "Стороны составили настоящий документ о нижеследующем."
    ]


def _subject_paragraphs(document: SmartDocument) -> list[str]:
    meta = document.metadata
    stage = f" на стадии «{meta.project_stage}»" if meta.project_stage else ""
    sentences = [
        "Исполнитель выполняет работы по подготовке документации"
        f"{stage} для объекта «{meta.object_name}»."
    ]
    if meta.address:
        sentences.append(f"Местонахождение объекта: {meta.address}.")
    if meta.document_cipher:
        sentences.append(f"Обозначение результата работ — {meta.document_cipher}.")
    return [" ".join(sentences)]


def _obligations_paragraphs(document: SmartDocument) -> list[str]:
    del document
    return [
        "Исполнитель разрабатывает документацию в объёме, определённом предметом, "
        "и передаёт результат заказчику.",
        "Заказчик передаёт исходные данные, рассматривает результат и направляет замечания "
        "в письменной форме.",
        "Стороны обеспечивают согласованность числовых характеристик документа "
        "с переданными исходными данными.",
    ]


def _delivery_paragraphs(document: SmartDocument) -> list[str]:
    meta = document.metadata
    sentences = ["Результат работ передаётся в виде оформленного текстового документа."]
    if meta.year:
        sentences.append(f"Год передачи результата — {meta.year}.")
    sentences.append("Факт передачи фиксируется актом сдачи-приёмки.")
    return [" ".join(sentences)]


def _details_paragraphs(document: SmartDocument) -> list[str]:
    meta = document.metadata
    paragraphs = [
        f"Исполнитель: {_party(meta.designer, 'не указан')}.",
        f"Заказчик: {_party(meta.customer, 'не указан')}.",
    ]
    if meta.chief_engineer:
        paragraphs.append(f"Главный инженер проекта: {meta.chief_engineer}.")
    if meta.address:
        paragraphs.append(f"Адрес объекта: {meta.address}.")
    return paragraphs


_SYNTHETIC: dict[str, SyntheticBuilder] = {
    "general": _general_paragraphs,
    "basis": _basis_paragraphs,
    "norms": _norms_paragraphs,
    "purpose": _purpose_paragraphs,
    "docs": _docs_paragraphs,
    "acceptance": _acceptance_paragraphs,
    "preamble": _preamble_paragraphs,
    "subject": _subject_paragraphs,
    "obligations": _obligations_paragraphs,
    "delivery": _delivery_paragraphs,
    "details": _details_paragraphs,
}
