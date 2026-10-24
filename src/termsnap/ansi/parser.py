"""
Главная функция разбора: поток терминала -> строки со стилями.
"""

from termsnap.ansi.canvas import Canvas
from termsnap.ansi.tokens import TOKEN
from termsnap.model import Line


def parse(text: str) -> tuple[Line, ...]:
    """
    Строки со стилями из текста с ANSI-последовательностями.
    """
    canvas = Canvas()
    for token in TOKEN.finditer(text):
        match token.lastgroup:
            case "text":
                canvas.write(token.group())
            case "control":
                canvas.control(token.group())
            case "final":
                canvas.csi(token.group("params"), token.group("final"))
    return canvas.lines()
