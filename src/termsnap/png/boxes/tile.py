"""
Клетка, в которой рисуется один символ псевдографики.
"""

from dataclasses import dataclass

from PIL import ImageDraw

from termsnap.png.pixels import Channels, fill_rect


@dataclass(frozen=True, slots=True)
class Tile:
    """
    Клетка символа: холст, границы (левый, верхний, правый, нижний край в пикселях), цвета текста и фона и толщина
    тонкой линии. Границы дробные: клетка бывает шире целого числа пикселей.
    """

    draw: ImageDraw.ImageDraw
    left: float
    top: float
    right: float
    bottom: float
    foreground: Channels
    background: Channels
    light: int

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def center_x(self) -> float:
        return (self.left + self.right) / 2

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2

    def fill(self, x0: float, y0: float, x1: float, y1: float, color: Channels | None = None) -> None:
        """
        Закрашивает прямоугольник цветом текста (или заданным цветом).
        """
        fill_rect(self.draw, x0, y0, x1, y1, self.foreground if color is None else color)
