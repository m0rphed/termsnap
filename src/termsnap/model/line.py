"""
Фрагменты и строки вывода.
"""

from dataclasses import dataclass

from termsnap.model.style import PLAIN, Style
from termsnap.width import text_width


@dataclass(frozen=True, slots=True)
class Span:
    """
    Фрагмент строки с одним стилем.
    """

    text: str
    style: Style = PLAIN

    @property
    def width(self) -> int:
        """
        Ширина фрагмента в клетках терминала (эмодзи и иероглифы занимают две клетки).
        """
        return text_width(self.text)


@dataclass(frozen=True, slots=True)
class Line:
    """
    Строка вывода: последовательность фрагментов; соседние фрагменты всегда отличаются стилем.
    """

    spans: tuple[Span, ...] = ()

    @property
    def text(self) -> str:
        """
        Текст строки без оформления.
        """
        return "".join(span.text for span in self.spans)

    @property
    def width(self) -> int:
        """
        Ширина строки в клетках терминала.
        """
        return sum(span.width for span in self.spans)
