"""Доступ к зарегистрированным профилям шаблонов."""

from __future__ import annotations

from collections.abc import Iterable

from smart2docx.errors import TemplateNotFoundError
from smart2docx.templates.profile import TemplateProfile
from smart2docx.templates.profiles import DEFAULT_PROFILES


class TemplateRegistry:
    """Хранит профили шаблонов и выдаёт их по идентификатору."""

    def __init__(self, profiles: Iterable[TemplateProfile] | None = None) -> None:
        self._items: dict[str, TemplateProfile] = {}
        for profile in DEFAULT_PROFILES if profiles is None else profiles:
            self.register(profile)

    def register(self, profile: TemplateProfile) -> None:
        """Добавляет или заменяет профиль с тем же идентификатором."""
        self._items[profile.id] = profile

    def get(self, template_id: str) -> TemplateProfile:
        """Возвращает профиль либо сообщает, что идентификатор неизвестен."""
        try:
            return self._items[template_id]
        except KeyError as exc:
            raise TemplateNotFoundError(template_id) from exc

    def list(self) -> list[TemplateProfile]:
        """Возвращает профили в алфавитном порядке идентификаторов."""
        return [self._items[key] for key in sorted(self._items)]
