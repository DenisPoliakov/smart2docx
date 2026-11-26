"""Профили шаблонов ГОСТ и доступ к ним."""

from smart2docx.templates.profile import PageSetup, SectionSlot, TemplateProfile, Typography
from smart2docx.templates.profiles import CONTRACT, DEFAULT_PROFILES, EXPLANATORY_NOTE, TECH_SPEC
from smart2docx.templates.registry import TemplateRegistry

__all__ = [
    "CONTRACT",
    "DEFAULT_PROFILES",
    "EXPLANATORY_NOTE",
    "PageSetup",
    "SectionSlot",
    "TECH_SPEC",
    "TemplateProfile",
    "TemplateRegistry",
    "Typography",
]
