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
from termsnap.theme import DARK, LIGHT, Theme

__all__ = [
    "DARK",
    "LIGHT",
    "PLAIN",
    "Backend",
    "Capture",
    "Color",
    "Indexed",
    "Line",
    "PipeBackend",
    "PtyBackend",
    "RawResult",
    "Request",
    "Rgb",
    "RunTimeout",
    "Span",
    "Style",
    "TermsnapError",
    "Theme",
    "apply_sgr",
    "parse",
    "run",
    "terminal_environment",
]
