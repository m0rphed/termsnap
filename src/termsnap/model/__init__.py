"""
Модель размеченного вывода терминала: цвета, стиль, фрагменты и строки.

Модель не зависит ни от способа получения вывода (канал, псевдотерминал), ни от способа показа (Word, SVG, PNG):
она описывает только то, что напечатано и каким стилем.

    Line
      Span "error: "  Style(fg=Indexed(1), bold=True)
      Span "file.py"  Style()
"""

from termsnap.model.color import PALETTE_SIZE, Color, Indexed, Rgb
from termsnap.model.line import Line, Span
from termsnap.model.style import PLAIN, Style

__all__ = ["PALETTE_SIZE", "PLAIN", "Color", "Indexed", "Line", "Rgb", "Span", "Style"]
