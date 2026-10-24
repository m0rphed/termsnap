"""
Цвета, которые встречаются в выводе терминала: из палитры или произвольные 24-битные.
"""

from dataclasses import dataclass

#: Сколько цветов в палитре терминала: 0-7 обычные, 8-15 яркие, 16-255 расширенная палитра xterm.
PALETTE_SIZE = 256


@dataclass(frozen=True, slots=True)
class Indexed:
    """
    Цвет из палитры терминала: 0-7 обычные, 8-15 яркие, 16-255 расширенная палитра (куб 6x6x6 и оттенки серого).
    Какой именно цвет получится, решает тема (``Theme``).
    """

    index: int

    def __post_init__(self) -> None:
        if not 0 <= self.index < PALETTE_SIZE:
            raise ValueError(f"индекс цвета должен быть от 0 до {PALETTE_SIZE - 1}, получено {self.index}")


@dataclass(frozen=True, slots=True)
class Rgb:
    """
    Цвет в 24-битном представлении.
    """

    red: int
    green: int
    blue: int

    def __post_init__(self) -> None:
        if not all(0 <= channel <= 255 for channel in self.channels):
            raise ValueError(f"каналы цвета должны быть от 0 до 255, получено {self.red}, {self.green}, {self.blue}")

    @classmethod
    def from_hex(cls, digits: str) -> "Rgb":
        """
        Цвет из шести шестнадцатеричных цифр (``"cd3131"``, ``#`` в начале необязателен); иначе ``ValueError``.
        """
        digits = digits.removeprefix("#")
        if len(digits) != 6:
            raise ValueError(f"нужно шесть шестнадцатеричных цифр, получено {digits!r}")
        return cls(int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))

    @property
    def channels(self) -> tuple[int, int, int]:
        """
        Каналы тройкой ``(красный, зеленый, синий)``: в таком виде их принимает Pillow.
        """
        return self.red, self.green, self.blue

    @property
    def hex(self) -> str:
        """
        Запись вида ``#rrggbb``.
        """
        return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"


type Color = Indexed | Rgb
