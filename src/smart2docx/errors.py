"""Ошибки модуля, которые обрабатывает HTTP-слой."""


class Smart2DocxError(Exception):
    """Базовая ошибка модуля."""


class DocumentParseError(Smart2DocxError):
    """Входной smart-документ не разобран или не прошёл проверку схемы."""


class TemplateNotFoundError(Smart2DocxError):
    """Профиль шаблона с указанным идентификатором не зарегистрирован."""

    def __init__(self, template_id: str) -> None:
        self.template_id = template_id
        super().__init__(f"Шаблон «{template_id}» не зарегистрирован.")
