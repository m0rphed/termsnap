"""
Линии рамок: тонкие, толстые и двойные рукава, сходящиеся в центре клетки.
"""

from termsnap.png.boxes.arc import draw_arc
from termsnap.png.boxes.arms import DOUBLE, HEAVY, THIN, Arms
from termsnap.png.boxes.tile import Tile

#: Половина расстояния между линиями двойной рамки: не меньше двух пикселей (чтобы между линиями оставался просвет
#: даже при самой тонкой линии), а при толстой линии - в 1.6 раза больше ее толщины.
_DOUBLE_MIN_OFFSET = 2.0
_DOUBLE_OFFSET_PER_LIGHT = 1.6


def heavy_width(light: int) -> int:
    """
    Толщина толстой линии при толщине тонкой ``light``: вдвое больше и еще пиксель, чтобы центр оставался посередине.
    """
    return light * 2 + 1


def double_offset(light: int) -> float:
    """
    Расстояние от оси до каждой из двух линий двойной рамки при толщине тонкой линии ``light``.
    """
    return max(_DOUBLE_MIN_OFFSET, light * _DOUBLE_OFFSET_PER_LIGHT)


def draw_lines(tile: Tile, arms: Arms) -> None:
    """
    Рисует символ рамки по его рукавам: скругленный угол - дугой, остальное - прямоугольниками от края клетки к
    центру.
    """
    if arms.arc and (arms.up or arms.down) and (arms.left or arms.right):
        draw_arc(tile, arms)
        return
    _draw_plain_arms(tile, arms)
    # двойной рукав - две параллельные линии; концы у центра зависят от соседних рукавов, чтобы линии смыкались
    _draw_double_vertical(tile, arms, -1, arms.up, arms.down)
    _draw_double_vertical(tile, arms, 1, arms.down, arms.up)
    _draw_double_horizontal(tile, arms, -1, arms.left, arms.right)
    _draw_double_horizontal(tile, arms, 1, arms.right, arms.left)


def _draw_plain_arms(tile: Tile, arms: Arms) -> None:
    """
    Тонкие и толстые рукава: прямоугольник от края клетки через центр до противоположной стороны линии.
    """
    cx, cy = tile.center_x, tile.center_y
    for name, weight in (("up", arms.up), ("down", arms.down), ("left", arms.left), ("right", arms.right)):
        if weight not in {THIN, HEAVY}:
            continue
        t = tile.light if weight == THIN else heavy_width(tile.light)
        if name == "up":
            tile.fill(cx - t / 2, tile.top, cx + t / 2, cy + t / 2)
        elif name == "down":
            tile.fill(cx - t / 2, cy - t / 2, cx + t / 2, tile.bottom)
        elif name == "left":
            tile.fill(tile.left, cy - t / 2, cx + t / 2, cy + t / 2)
        else:
            tile.fill(cx - t / 2, cy - t / 2, tile.right, cy + t / 2)


def _draw_double_vertical(tile: Tile, arms: Arms, direction: int, weight: int, opposite: int) -> None:
    """
    Двойной рукав вверх (``direction=-1``) или вниз (``1``): две вертикальные линии по сторонам от оси. У центра
    каждая линия кончается там, где ей положено замкнуться с перпендикулярными рукавами:

        рядом с линией (с ее стороны) есть боковой рукав -> идет до дальней его линии
        боковой рукав только с другой стороны (и встречный рукав не двойной) -> до ближней
        иначе -> до центра
    """
    if weight != DOUBLE:
        return
    cx, cy, light, offset = tile.center_x, tile.center_y, tile.light, double_offset(tile.light)
    for side in (-1, 1):
        beside, across = (arms.left, arms.right) if side == -1 else (arms.right, arms.left)
        if beside:
            end = cy + direction * offset
        elif across and opposite != DOUBLE:
            end = cy - direction * offset
        else:
            end = cy
        edge = tile.top if direction < 0 else tile.bottom
        x = cx + side * offset
        tile.fill(x - light / 2, edge, x + light / 2, end - direction * light / 2)


def _draw_double_horizontal(tile: Tile, arms: Arms, direction: int, weight: int, opposite: int) -> None:
    """
    То же для двойного рукава влево (``direction=-1``) или вправо (``1``); см. ``_draw_double_vertical``.
    """
    if weight != DOUBLE:
        return
    cx, cy, light, offset = tile.center_x, tile.center_y, tile.light, double_offset(tile.light)
    for side in (-1, 1):
        beside, across = (arms.up, arms.down) if side == -1 else (arms.down, arms.up)
        if beside:
            end = cx + direction * offset
        elif across and opposite != DOUBLE:
            end = cx - direction * offset
        else:
            end = cx
        edge = tile.left if direction < 0 else tile.right
        y = cy + side * offset
        tile.fill(edge, y - light / 2, end - direction * light / 2, y + light / 2)
