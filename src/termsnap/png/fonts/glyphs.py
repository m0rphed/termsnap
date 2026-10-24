"""
Есть ли в шрифте глиф символа.
"""

from PIL import Image, ImageDraw, ImageFont

from termsnap.png.fonts.face import Face

#: Код, которого заведомо нет ни в одном шрифте (последняя позиция Unicode): на нем рисуется знак "нет глифа".
_ABSENT_CODE_POINT = "\U0010ffff"

#: Размер, в котором шрифт открывается для проверки покрытия. Достаточно, чтобы глифы различались по картинке.
_PROBE_SIZE = 24


def _picture(font: ImageFont.FreeTypeFont, char: str) -> bytes:
    """
    Как символ выглядит в шрифте: яркости точек на небольшом листе.
    """
    side = round(font.size * 2)
    sheet = Image.new("L", (side, side))
    ImageDraw.Draw(sheet).text((0, 0), char, font=font, fill=255)
    return sheet.tobytes()


def has_glyph(font: ImageFont.FreeTypeFont, char: str) -> bool:
    """
    Есть ли в шрифте символ. Pillow не говорит о покрытии напрямую: у отсутствующего символа рисуется тот же знак
    "нет глифа" (обычно рамка), что и у заведомо незанятого кода, поэтому картинки сравниваются.

        есть = картинка(char) != картинка(код, которого нет ни в одном шрифте)
    """
    return _picture(font, char) != _picture(font, _ABSENT_CODE_POINT)


def missing_glyphs(face: Face, chars: str) -> str:
    """
    Символы из ``chars`` (без пробельных и управляющих), которых нет в шрифте, в порядке кодов.
    """
    font = ImageFont.truetype(str(face.path), size=_PROBE_SIZE, index=face.index)
    wanted = {char for char in chars if char.isprintable() and not char.isspace()}
    return "".join(sorted(char for char in wanted if not has_glyph(font, char)))
