"""
Рисование псевдографики самой библиотекой: рамки (U+2500-257F), блочные элементы (U+2580-259F) и шрифт Брайля
(U+2800-28FF).

Глифы этих символов в шрифтах не рассчитаны на межстрочный интервал: рамки получаются с разрывами между строками,
а блоки не закрашивают клетку целиком. Терминалы поэтому рисуют такие символы сами по геометрии клетки, так
делаем и мы: символ закрашивает прямоугольник клетки (от верха строки до низа), и соседние клетки смыкаются.
"""

import unicodedata
from dataclasses import dataclass
from functools import cache

from PIL import ImageDraw

#: Квадранты блочных символов U+2596-259F: какие четверти клетки закрашены (верх-лево, верх-право, низ-лево, низ-право).
_QUADRANTS = {
    0x2596: (0, 0, 1, 0),
    0x2597: (0, 0, 0, 1),
    0x2598: (1, 0, 0, 0),
    0x2599: (1, 0, 1, 1),
    0x259A: (1, 0, 0, 1),
    0x259B: (1, 1, 1, 0),
    0x259C: (1, 1, 0, 1),
    0x259D: (0, 1, 0, 0),
    0x259E: (0, 1, 1, 0),
    0x259F: (0, 1, 1, 1),
}

#: Доля цвета текста в закраске штриховых блоков (светлая, средняя и темная).
_SHADES = {0x2591: 0.25, 0x2592: 0.5, 0x2593: 0.75}

_WEIGHTS = {"LIGHT": 1, "SINGLE": 1, "HEAVY": 2, "DOUBLE": 3}
_DIRECTIONS = {
    "UP": ("up",),
    "DOWN": ("down",),
    "LEFT": ("left",),
    "RIGHT": ("right",),
    "VERTICAL": ("up", "down"),
    "HORIZONTAL": ("left", "right"),
}
_DASH_WORDS = {"DOUBLE", "TRIPLE", "QUADRUPLE", "DASH"}

#: Точки символа Брайля: бит -> (столбец, строка) в сетке 2x4.
_BRAILLE = {0: (0, 0), 1: (0, 1), 2: (0, 2), 3: (1, 0), 4: (1, 1), 5: (1, 2), 6: (0, 3), 7: (1, 3)}


@dataclass(frozen=True, slots=True)
class Arms:
    """
    Рукава символа рамки от центра клетки: толщина каждого (0 - нет, 1 - тонкая, 2 - толстая, 3 - двойная).
    """

    up: int = 0
    down: int = 0
    left: int = 0
    right: int = 0
    arc: bool = False


@cache
def arms_of(char: str) -> Arms | None:
    """
    Рукава символа рамки по его названию Unicode («BOX DRAWINGS LIGHT DOWN AND RIGHT»); ``None`` для остальных
    символов и для диагоналей. Штриховые линии рисуются сплошными.
    """
    if not "─" <= char <= "╿":
        return None
    words = unicodedata.name(char, "").removeprefix("BOX DRAWINGS ").split()
    if "DIAGONAL" in words:
        return None
    arc = "ARC" in words
    words = [word for word in words if word != "ARC"]
    if "DASH" in words:
        words = [word for word in words if word not in _DASH_WORDS]
    parts = [part.split() for part in " ".join(words).split(" AND ")]
    weights = [next((_WEIGHTS[word] for word in part if word in _WEIGHTS), None) for part in parts]
    default = next((weight for weight in weights if weight is not None), 1)
    result = {"up": 0, "down": 0, "left": 0, "right": 0}
    for part, weight in zip(parts, weights, strict=True):
        for word in part:
            for direction in _DIRECTIONS.get(word, ()):
                result[direction] = weight or default
    return Arms(**result, arc=arc)


def _fill(draw: ImageDraw.ImageDraw, x0: float, y0: float, x1: float, y1: float, color: tuple[int, int, int]) -> None:
    """
    Закрашивает прямоугольник [x0, x1) x [y0, y1) в пикселях (границы округляются, минимум один пиксель).
    """
    left, right = round(min(x0, x1)), round(max(x0, x1))
    top, bottom = round(min(y0, y1)), round(max(y0, y1))
    if right > left and bottom > top:
        draw.rectangle((left, top, right - 1, bottom - 1), fill=color)


def _blend(foreground: tuple[int, int, int], background: tuple[int, int, int], share: float) -> tuple[int, int, int]:
    r, g, b = (round(f * share + k * (1 - share)) for f, k in zip(foreground, background, strict=True))
    return r, g, b


def _draw_lines(
    draw: ImageDraw.ImageDraw,
    arms: Arms,
    box: tuple[float, float, float, float],
    color: tuple[int, int, int],
    light: int,
) -> None:
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    heavy = light * 2 + 1
    offset = max(2.0, light * 1.6)  # половина расстояния между линиями двойной рамки

    if arms.arc and (arms.up or arms.down) and (arms.left or arms.right):
        _draw_arc(draw, arms, box, color, light)
        return

    # одинарные и толстые рукава: прямоугольник от края клетки через центр
    for name, weight in (("up", arms.up), ("down", arms.down), ("left", arms.left), ("right", arms.right)):
        if weight not in {1, 2}:
            continue
        t = light if weight == 1 else heavy
        if name == "up":
            _fill(draw, cx - t / 2, y0, cx + t / 2, cy + t / 2, color)
        elif name == "down":
            _fill(draw, cx - t / 2, cy - t / 2, cx + t / 2, y1, color)
        elif name == "left":
            _fill(draw, x0, cy - t / 2, cx + t / 2, cy + t / 2, color)
        else:
            _fill(draw, cx - t / 2, cy - t / 2, x1, cy + t / 2, color)

    # двойные рукава: две параллельные линии; концы у центра зависят от соседних рукавов, чтобы линии смыкались
    def vertical(direction: int, weight: int, opposite: int) -> None:
        if weight != 3:
            return
        for side in (-1, 1):
            beside, across = (arms.left, arms.right) if side == -1 else (arms.right, arms.left)
            if beside:
                end = cy + direction * offset
            elif across and opposite != 3:
                end = cy - direction * offset
            else:
                end = cy
            edge = y0 if direction < 0 else y1
            x = cx + side * offset
            _fill(draw, x - light / 2, edge, x + light / 2, end - direction * light / 2, color)

    def horizontal(direction: int, weight: int, opposite: int) -> None:
        if weight != 3:
            return
        for side in (-1, 1):
            beside, across = (arms.up, arms.down) if side == -1 else (arms.down, arms.up)
            if beside:
                end = cx + direction * offset
            elif across and opposite != 3:
                end = cx - direction * offset
            else:
                end = cx
            edge = x0 if direction < 0 else x1
            y = cy + side * offset
            _fill(draw, edge, y - light / 2, end - direction * light / 2, y + light / 2, color)

    vertical(-1, arms.up, arms.down)
    vertical(1, arms.down, arms.up)
    horizontal(-1, arms.left, arms.right)
    horizontal(1, arms.right, arms.left)


def _draw_arc(
    draw: ImageDraw.ImageDraw,
    arms: Arms,
    box: tuple[float, float, float, float],
    color: tuple[int, int, int],
    light: int,
) -> None:
    """
    Скругленный угол (U+256D-2570): четверть эллипса между серединами сторон клетки и прямые концы до границы.
    """
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = x1 - x0, y1 - y0
    if arms.down and arms.right:
        bbox, angles = (cx, cy, cx + w, cy + h), (180, 270)
    elif arms.down and arms.left:
        bbox, angles = (cx - w, cy, cx, cy + h), (270, 360)
    elif arms.up and arms.right:
        bbox, angles = (cx, cy - h, cx + w, cy), (90, 180)
    else:
        bbox, angles = (cx - w, cy - h, cx, cy), (0, 90)
    draw.arc(bbox, angles[0], angles[1], fill=color, width=light)
    t = light / 2
    if arms.down:
        _fill(draw, cx - t, cy + h / 2 - 1, cx + t, y1, color)
    if arms.up:
        _fill(draw, cx - t, y0, cx + t, cy - h / 2 + 1, color)
    if arms.right:
        _fill(draw, cx + w / 2 - 1, cy - t, x1, cy + t, color)
    if arms.left:
        _fill(draw, x0, cy - t, cx - w / 2 + 1, cy + t, color)


def draw_cell(
    draw: ImageDraw.ImageDraw,
    char: str,
    box: tuple[float, float, float, float],
    foreground: tuple[int, int, int],
    background: tuple[int, int, int],
    light: int,
) -> bool:
    """
    Рисует символ псевдографики в клетке ``box`` = (левый, верхний, правый, нижний край) и возвращает ``True``;
    для остальных символов ничего не рисует и возвращает ``False`` (их рисует шрифт). ``light`` - толщина
    тонкой линии в пикселях.
    """
    if len(char) != 1:
        return False
    code = ord(char)
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if 0x2500 <= code <= 0x257F:
        arms = arms_of(char)
        if arms is None:
            return False
        _draw_lines(draw, arms, box, foreground, light)
    elif code == 0x2580:  # верхняя половина
        _fill(draw, x0, y0, x1, y0 + h / 2, foreground)
    elif 0x2581 <= code <= 0x2588:  # нижние доли от 1/8 до целого
        _fill(draw, x0, y1 - h * (code - 0x2580) / 8, x1, y1, foreground)
    elif 0x2589 <= code <= 0x258F:  # левые доли от 7/8 до 1/8
        _fill(draw, x0, y0, x0 + w * (0x2590 - code) / 8, y1, foreground)
    elif code == 0x2590:  # правая половина
        _fill(draw, x0 + w / 2, y0, x1, y1, foreground)
    elif code in _SHADES:
        _fill(draw, x0, y0, x1, y1, _blend(foreground, background, _SHADES[code]))
    elif code == 0x2594:  # верхняя 1/8
        _fill(draw, x0, y0, x1, y0 + h / 8, foreground)
    elif code == 0x2595:  # правая 1/8
        _fill(draw, x1 - w / 8, y0, x1, y1, foreground)
    elif code in _QUADRANTS:
        for quadrant, filled in zip(((0, 0), (1, 0), (0, 1), (1, 1)), _QUADRANTS[code], strict=True):
            if filled:
                column, row = quadrant
                _fill(
                    draw,
                    x0 + w * column / 2,
                    y0 + h * row / 2,
                    x0 + w * (column + 1) / 2,
                    y0 + h * (row + 1) / 2,
                    foreground,
                )
    elif 0x2800 <= code <= 0x28FF:
        radius = min(w * 0.14, h * 0.08)
        for bit, (column, row) in _BRAILLE.items():
            if ((code - 0x2800) >> bit) & 1:
                x, y = x0 + w * (0.28 + 0.44 * column), y0 + h * (0.125 + 0.25 * row)
                draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=foreground)
    else:
        return False
    return True


def is_box_char(char: str) -> bool:
    """
    Рисуется ли символ самой библиотекой (``draw_cell`` вернет ``True``).
    """
    code = ord(char) if len(char) == 1 else 0
    if 0x2500 <= code <= 0x257F:
        return arms_of(char) is not None
    return 0x2580 <= code <= 0x259F or 0x2800 <= code <= 0x28FF


__all__ = ["Arms", "arms_of", "draw_cell", "is_box_char"]
