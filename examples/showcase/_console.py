"""
Консоль rich для примеров: на Windows при выводе в канал rich сам переходит в режим ``legacy_windows`` (проверяет
дескриптор консоли, а не переменные окружения) и печатает текст без стилей, поэтому режим задается явно.
"""

from rich.console import Console


def make(**options: object) -> Console:
    _options = {
        "force_terminal": True,
        "legacy_windows": False,
        "color_system": "256",
        **options,
    }
    return Console(**_options)  # type: ignore[arg-type]
