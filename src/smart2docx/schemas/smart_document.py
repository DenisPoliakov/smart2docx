"""Схема машиночитаемого smart-документа."""

from __future__ import annotations

from collections.abc import Iterator

from pydantic import Field, field_validator

from smart2docx.schemas.base import SchemaModel


def _coerce_scalar(value: object) -> object:
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return format(value, "f").rstrip("0").rstrip(".")
    return value


class ProjectMetadata(SchemaModel):
    """Реквизиты объекта и комплекта документации."""

    object_name: str = Field(min_length=1, description="Наименование объекта")
    object_code: str | None = Field(default=None, description="Код объекта")
    document_cipher: str | None = Field(default=None, description="Обозначение документа")
    project_stage: str | None = Field(default=None, description="Стадия проектирования")
    address: str | None = Field(default=None, description="Адрес объекта")
    customer: str | None = Field(default=None, description="Заказчик")
    designer: str | None = Field(default=None, description="Проектировщик")
    chief_engineer: str | None = Field(default=None, description="Главный инженер проекта")
    year: int | None = Field(default=None, description="Год разработки")

    @field_validator(
        "object_code",
        "document_cipher",
        "project_stage",
        "address",
        "customer",
        "designer",
        "chief_engineer",
        mode="before",
    )
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("year", mode="before")
    @classmethod
    def _coerce_year(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            if stripped.isdigit():
                return int(stripped)
        return value

    @field_validator("year")
    @classmethod
    def _check_year(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if not 1900 <= value <= 2100:
            raise ValueError("год должен быть в диапазоне от 1900 до 2100")
        return value


class Parameter(SchemaModel):
    """Именованная характеристика раздела."""

    name: str = Field(min_length=1)
    value: str = Field(min_length=1)
    unit: str | None = None
    note: str | None = None

    @field_validator("value", mode="before")
    @classmethod
    def _coerce_value(cls, value: object) -> object:
        return _coerce_scalar(value)

    @field_validator("unit", "note", mode="before")
    @classmethod
    def _blank_optional(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class Requirement(SchemaModel):
    """Нормативное или проектное требование."""

    text: str = Field(min_length=1)
    code: str | None = None
    source: str | None = None

    @field_validator("code", "source", mode="before")
    @classmethod
    def _blank_optional(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class TableColumn(SchemaModel):
    """Столбец таблицы характеристик."""

    key: str = Field(min_length=1)
    title: str = Field(min_length=1)


class CharacteristicTable(SchemaModel):
    """Таблица характеристик с фиксированным набором столбцов."""

    title: str = Field(min_length=1)
    columns: list[TableColumn] = Field(min_length=1)
    rows: list[dict[str, str]] = Field(default_factory=list)

    @field_validator("rows", mode="before")
    @classmethod
    def _coerce_rows(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        normalized: list[dict[str, str]] = []
        for row in value:
            if not isinstance(row, dict):
                raise ValueError("строка таблицы должна быть объектом")
            normalized.append(
                {
                    str(key).strip(): ""
                    if cell is None
                    else str(_coerce_scalar(cell)).strip()
                    for key, cell in row.items()
                }
            )
        return normalized

    @field_validator("columns")
    @classmethod
    def _unique_keys(cls, columns: list[TableColumn]) -> list[TableColumn]:
        keys = [column.key for column in columns]
        if len(keys) != len(set(keys)):
            raise ValueError("ключи столбцов должны быть уникальны")
        return columns


class SmartSection(SchemaModel):
    """Раздел smart-документа и его вложенные подразделы."""

    code: str = Field(min_length=1, description="Код раздела во внешней системе")
    title: str = Field(min_length=1, description="Наименование раздела")
    content: str | None = Field(default=None, description="Исходный текст или факты")
    parameters: list[Parameter] = Field(default_factory=list)
    requirements: list[Requirement] = Field(default_factory=list)
    tables: list[CharacteristicTable] = Field(default_factory=list)
    subsections: list[SmartSection] = Field(default_factory=list)

    @field_validator("content", mode="before")
    @classmethod
    def _blank_content(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class SmartDocument(SchemaModel):
    """Единая внутренняя модель smart-документа."""

    metadata: ProjectMetadata
    document_type: str | None = Field(
        default=None,
        description="Тип описания во внешней системе. На выбор шаблона не влияет.",
    )
    sections: list[SmartSection] = Field(min_length=1)

    @field_validator("document_type", mode="before")
    @classmethod
    def _blank_document_type(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    def walk_sections(self) -> Iterator[SmartSection]:
        """Обходит разделы в порядке исходного документа, включая вложенные."""

        def walk(section: SmartSection) -> Iterator[SmartSection]:
            yield section
            for child in section.subsections:
                yield from walk(child)

        for section in self.sections:
            yield from walk(section)


SmartSection.model_rebuild()
