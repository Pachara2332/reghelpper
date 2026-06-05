"""Bilingual text system – choose Thai or English at runtime."""

from enum import Enum


class Lang(Enum):
    TH = "th"
    EN = "en"


# Global language setting
_current_lang = Lang.TH


def set_lang(lang: Lang):
    global _current_lang
    _current_lang = lang


def get_lang() -> Lang:
    return _current_lang


def t(thai: str, english: str) -> str:
    """Return text in the current language."""
    return thai if _current_lang == Lang.TH else english
