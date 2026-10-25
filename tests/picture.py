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

import io
import textwrap
from collections.abc import Mapping, Sequence

from PIL import Image

from termsnap import Line, Span
from termsnap.png import FontSet, render_image, render_png

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


def check_snapshot_picture(lines: Sequence[Line], fonts: FontSet) -> None:
    """
    PNG снимка экрана: размер получается из размера снимка (столбцы x ширина клетки, строки x высота строки), а на
    картинке есть и фон, и нарисованное. Размеры клетки берутся из картинок, нарисованных тем же шрифтом, поэтому числа
    не зависят от шрифта. Ширина клетки может быть дробной (движок раскладки raqm), а ширина картинки округляется до
    пикселя, поэтому ширина сверяется с точностью до одного пикселя.
    """
    options = {"fonts": fonts, "scale": 1, "padding": 0, "font_size": 12}
    image = Image.open(io.BytesIO(render_png(lines, **options)))
    many = 1000  # много клеток подряд: дробная ширина клетки получается с точностью до тысячной доли пикселя
    cell_width = render_image([Line((Span("M" * many),))], **options).width / many
    row_height = render_image([Line((Span("M"),))], **options).height
    columns = max((line.width for line in lines), default=1)
    assert abs(image.width - columns * cell_width) <= 1
    assert image.height == row_height * len(lines)
    assert len(image.convert("RGB").getcolors(maxcolors=image.width * image.height) or []) >= 2
