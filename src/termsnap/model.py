"""
Модель размеченного вывода терминала: цвета, стиль, фрагменты и строки.

Модель не зависит ни от способа получения вывода (канал, псевдотерминал), ни от способа показа (Word, SVG, PNG):
она описывает только то, что напечатано и каким стилем.
"""

from dataclasses import dataclass

from termsnap.width import text_width


@dataclass(frozen=True, slots=True)
class Indexed:
    """
    Цвет из палитры терминала: 0-7 обычные, 8-15 яркие, 16-255 расширенная палитра (куб 6x6x6 и оттенки серого).
    Какой именно цвет получится, решает тема (``Theme``).
    """

    index: int

    def __post_init__(self) -> None:
        if not 0 <= self.index <= 255:
            raise ValueError(f"индекс цвета должен быть от 0 до 255, получено {self.index}")


@dataclass(frozen=True, slots=True)
class Rgb:
    """
    Цвет в 24-битном представлении.
    """

    red: int
    green: int
    blue: int

    def __post_init__(self) -> None:
        if not all(0 <= channel <= 255 for channel in (self.red, self.green, self.blue)):
            raise ValueError(f"каналы цвета должны быть от 0 до 255, получено {self.red}, {self.green}, {self.blue}")

    @property
    def hex(self) -> str:
        """
        Запись вида ``#rrggbb``.
        """
        return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"


type Color = Indexed | Rgb


@dataclass(frozen=True, slots=True, kw_only=True)
class Style:
    """
    Оформление фрагмента текста. ``fg`` и ``bg`` равны ``None``, если цвет не задан (цвет по умолчанию темы).
    """

    fg: Color | None = None
    bg: Color | None = None
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    inverse: bool = False


#: Стиль по умолчанию: ничего не задано.
PLAIN = Style()


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
