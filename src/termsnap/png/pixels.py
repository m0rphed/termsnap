"""
Пиксельная арифметика, общая для рисования текста и псевдографики.
"""

import math

from PIL import ImageDraw

#: Цвет как тройка каналов 0-255: в таком виде его принимает Pillow.
type Channels = tuple[int, int, int]


def pixel(value: float) -> int:
    """
    Номер пикселя границы: округление "половинки вверх", а не банковское ``round``. Банковское округляет
    9.5 и 10.5 в одно число, и линия толщиной в один пиксель вокруг целой координаты исчезает (при нечетной
    координате, наоборот, удваивается). Здесь края штриха сдвигаются вместе, поэтому его толщина не зависит от
    положения.
    """
    return math.floor(value + 0.5)


def fill_rect(draw: ImageDraw.ImageDraw, x0: float, y0: float, x1: float, y1: float, color: Channels) -> None:
    """
    Закрашивает прямоугольник [x0, x1) x [y0, y1) в пикселях. Границы округляются (``pixel``); если после
    округления ширина или высота нулевая, ничего не рисуется.
    """
    left, right = pixel(min(x0, x1)), pixel(max(x0, x1))
    top, bottom = pixel(min(y0, y1)), pixel(max(y0, y1))
    if right > left and bottom > top:
        draw.rectangle((left, top, right - 1, bottom - 1), fill=color)  # Pillow включает правый/нижний край


def blend(foreground: Channels, background: Channels, share: float) -> Channels:
    """
    Смесь цветов: ``share`` - доля ``foreground`` (0 - только фон, 1 - только передний цвет).
    """
    red, green, blue = (
        round(front * share + back * (1 - share)) for front, back in zip(foreground, background, strict=True)
    )
    return red, green, blue
