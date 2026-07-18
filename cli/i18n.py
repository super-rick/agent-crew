"""
Lightweight i18n module — no gettext, no external dependencies.

Language detection order:
    1. --lang CLI flag (stored via set_locale)
    2. LANG / LC_ALL / LC_MESSAGES environment variables
    3. Default: "zh" (中文)

Usage:
    from cli.i18n import _, set_locale, get_locale

    console.print(_("doctor.llm_ok", balance="42.30"))
    set_locale("en")
"""

from __future__ import annotations

import os
import threading

# Thread-local for safe concurrent use
_locale: str | None = None
_lock = threading.Lock()

SUPPORTED_LOCALES = {"zh", "en"}


def _detect_locale() -> str:
    """Detect preferred locale from environment variables.

    Checks LC_ALL, LC_MESSAGES, LANG in order.
    Returns "zh" if any variant contains "zh", otherwise "en".
    """
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        val = os.environ.get(var, "")
        if val:
            v = val.lower()
            if "zh" in v:
                return "zh"
            if "en" in v:
                return "en"
    return "zh"


def get_locale() -> str:
    """Return the current locale ('zh' or 'en')."""
    global _locale
    if _locale is not None:
        return _locale
    with _lock:
        if _locale is not None:
            return _locale
        _locale = _detect_locale()
    return _locale


def set_locale(locale: str) -> None:
    """Force a specific locale.

    Args:
        locale: 'zh' or 'en'.

    Raises:
        ValueError: If the locale is not supported.
    """
    global _locale
    locale = locale.lower()[:2]
    if locale not in SUPPORTED_LOCALES:
        raise ValueError(
            f"Unsupported locale '{locale}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_LOCALES))}"
        )
    _locale = locale


class _Translator:
    """Lazy-loading translator — defers message table import to avoid circular imports."""

    def __init__(self):
        self._messages: dict | None = None

    def _load(self) -> dict:
        if self._messages is not None:
            return self._messages
        from cli.i18n_messages import MESSAGES

        self._messages = MESSAGES
        return self._messages

    def __call__(self, key: str, **kwargs) -> str:
        """Translate a message key to the current locale.

        Args:
            key: Message key defined in i18n_messages.MESSAGES.
            **kwargs: Format variables for the message template.

        Fallback chain: current locale → "en" → key itself (never returns empty).
        """
        messages = self._load()
        locale = get_locale()
        entry = messages.get(key, {})

        if not isinstance(entry, dict):
            text = str(entry)
        else:
            text = entry.get(locale) or entry.get("en")

        if text is None:
            return key

        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text
        return text


# Singleton
_ = _Translator()
