"""
Запись цвета в любом из привычных видов.
"""

from termsnap.model import Rgb

#: Как можно записать цвет: ``Rgb``, строка ``"#rrggbb"`` или ``"#rgb"`` (``#`` необязателен), тройка чисел 0-255.
type ColorLike = Rgb | str | tuple[int, int, int]


def parse_color(value: ColorLike) -> Rgb:
    """
    Приводит цвет, записанный любым из способов (``ColorLike``), к ``Rgb``.
    """
    match value:
        case Rgb():
            return value
        case str():
            digits = value.strip().removeprefix("#")
            if len(digits) == 3:  # "#f80" - сокращенная запись "#ff8800"
                digits = "".join(char * 2 for char in digits)
            try:
                return Rgb.from_hex(digits)
            except ValueError:
                raise ValueError(f"цвет {value!r}: ожидается запись вида #rrggbb или #rgb") from None
        case (int(red), int(green), int(blue)):
            return Rgb(red, green, blue)
    raise TypeError(f"цвет {value!r}: ожидается Rgb, строка #rrggbb или тройка чисел")
