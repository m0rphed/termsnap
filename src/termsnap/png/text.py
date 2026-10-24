"""
Чем рисовать текст клетки: какое начертание взять для символа и что именно отдать Pillow.
"""

from functools import cache
from typing import NamedTuple

from PIL import ImageFont

from termsnap.png.fonts import Face, FontSet, fallback_fontsets, has_glyph
from termsnap.width import EMOJI_SELECTOR, TEXT_SELECTOR, ZERO_WIDTH_JOINER


class FaceChoice(NamedTuple):
    """
    Выбранное для символа начертание.
    """

    face: Face
    synthetic_bold: bool  # жирного начертания нет, жирность надо имитировать
    fallback: bool  # символа нет в основном шрифте, взят запасной (он может быть цветным, как эмодзи)


@cache
def load_font(face: Face, size: int) -> ImageFont.FreeTypeFont:
    """
    Шрифт ``face`` нужного размера (открытые шрифты запоминаются: открывать файл на каждый символ долго).
    """
    return ImageFont.truetype(str(face.path), size=size, index=face.index)


@cache
def _covers(face: Face, size: int, char: str) -> bool:
    try:
        return has_glyph(load_font(face, size), char)
    except OSError:  # растровые шрифты эмодзи с одним допустимым размером не открываются в произвольном
        return False


def drawn_text(cluster: str) -> str:
    """
    Что рисовать для клеточной группы: без селекторов начертания и без продолжения составного эмодзи (без
    библиотеки raqm Pillow не умеет их шаблонизировать и рисует "пустой" знак).
    """
    first_part = cluster.split(ZERO_WIDTH_JOINER)[0]
    return "".join(char for char in first_part if char not in {EMOJI_SELECTOR, TEXT_SELECTOR})


def choose_face(fonts: FontSet, size: int, char: str, *, bold: bool, italic: bool) -> FaceChoice:
    """
    Начертание для символа.

        основное начертание под жирность/курсив; если символ ASCII или глиф в нем есть -> оно
        иначе первое запасное семейство, в котором глиф есть  -> оно (fallback=True)
        иначе основное начертание (будет нарисован знак "нет глифа")
    """
    face, synthetic = fonts.pick(bold=bold, italic=italic)
    if char.isascii() or _covers(face, size, char):
        return FaceChoice(face, synthetic, False)
    for fallback in fallback_fontsets():
        alternative, alternative_synthetic = fallback.pick(bold=bold, italic=italic)
        if _covers(alternative, size, char):
            return FaceChoice(alternative, alternative_synthetic, True)
    return FaceChoice(face, synthetic, False)
