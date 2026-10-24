"""
Картинка как текст: ожидаемый результат рисования записывается в тесте рисунком из букв, и его видно глазами.

    EXPECTED = art('''
        ...#...
        ...#...
        ###.###
    ''')
    assert picture(image, {".": BACKGROUND, "#": FOREGROUND}) == EXPECTED

Каждый пиксель - одна буква из легенды (точный цвет -> буква). Пиксель, цвета которого в легенде нет, - ``+``: так
видны сглаженные края и ошибки. При падении теста pytest показывает два рисунка рядом, а не два списка чисел.
"""

import textwrap
from collections.abc import Mapping

from PIL import Image

type Rgb = tuple[int, int, int]

#: Буква для пикселя, цвета которого нет в легенде (сглаживание, смесь цветов, чужой цвет).
UNKNOWN = "+"


def art(text: str) -> str:
    """
    Рисунок из тройных кавычек: без общего отступа, без первой пустой строки и без завершающего перевода строки.
    """
    return textwrap.dedent(text).strip("\n")


def picture(image: Image.Image, legend: Mapping[str, Rgb], box: tuple[int, int, int, int] | None = None) -> str:
    """
    Картинка (или ее часть ``box`` = левый, верхний, правый, нижний край) буквами: ``legend`` сопоставляет букву цвету.
    """
    letters = {color: letter for letter, color in legend.items()}
    rgb = image.convert("RGB")
    left, top, right, bottom = box or (0, 0, rgb.width, rgb.height)
    rows = []
    for y in range(top, bottom):
        pixels = (rgb.getpixel((x, y)) for x in range(left, right))
        rows.append("".join(letters.get(pixel, UNKNOWN) for pixel in pixels))  # type: ignore[arg-type]
    return "\n".join(rows)


def cell_colors(image: Image.Image, columns: int, row: int = 0, rows: int = 1) -> list[Rgb]:
    """
    Цвет в середине каждой из ``columns`` клеток строки ``row`` (клетки идут вплотную, поля у картинки нет).
    """
    rgb = image.convert("RGB")
    y = round((row + 0.5) * rgb.height / rows)
    return [rgb.getpixel((round((column + 0.5) * rgb.width / columns), y)) for column in range(columns)]  # type: ignore[misc]
