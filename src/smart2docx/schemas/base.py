"""Общие настройки схем обмена."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


def to_camel(name: str) -> str:
    """Преобразует имя поля из snake_case в camelCase."""
    first, *rest = name.split("_")
    return first + "".join(part[:1].upper() + part[1:] for part in rest)


class SchemaModel(BaseModel):
    """Базовая схема входных данных.

    Принимает имена полей в snake_case и camelCase. Неизвестные поля
    не прерывают разбор: внешняя система может передавать служебные ключи.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        extra="ignore",
        str_strip_whitespace=True,
    )
