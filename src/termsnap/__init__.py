"""
termsnap - запуск команд и разбор их вывода с ANSI-цветами в нейтральную модель (строки, фрагменты, стили).

    from termsnap import run

    capture = run(["node", "app.js"])
    for line in capture.lines:
        for span in line.spans:
            print(span.style.fg, span.text)
"""

from termsnap.ansi import apply_sgr, parse
from termsnap.backends import Backend, PipeBackend, PtyBackend, RawResult, Request
from termsnap.errors import RunTimeout, TermsnapError
from termsnap.model import PLAIN, Color, Indexed, Line, Rgb, Span, Style
from termsnap.runner import Capture, run, terminal_environment
from termsnap.steps import Key, Keys, Pause, Snapshot, Step
from termsnap.theme import (
    ANSI_NAMES,
    DARK,
    LIGHT,
    THEMES,
    ColorLike,
    Theme,
    ThemeSpec,
    get_theme,
    parse_color,
    register_theme,
)

__all__ = [
    "ANSI_NAMES",
    "DARK",
    "LIGHT",
    "PLAIN",
    "THEMES",
    "Backend",
    "Capture",
    "Color",
    "ColorLike",
    "Indexed",
    "Key",
    "Keys",
    "Line",
    "Pause",
    "PipeBackend",
    "PtyBackend",
    "RawResult",
    "Request",
    "Rgb",
    "RunTimeout",
    "Snapshot",
    "Span",
    "Step",
    "Style",
    "TermsnapError",
    "Theme",
    "ThemeSpec",
    "apply_sgr",
    "get_theme",
    "parse",
    "parse_color",
    "register_theme",
    "run",
    "terminal_environment",
]
