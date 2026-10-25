"""
Две реализации одной модели: разбор потока для каналов (``ansi.parse``) и эмулятор экрана для псевдотерминала
(``screen.render``). На простом цветном тексте без перемещений курсора они обязаны давать одни и те же строки.

Потоки собираются случайно, но из фиксированного зерна: падение воспроизводится по номеру в названии теста.
"""

import random

import pytest
from support import require_module

require_module("pyte")

from termsnap import Line, parse
from termsnap.model import PLAIN, Style
from termsnap.screen import render

ESC = "\x1b"
COLUMNS = 80  # шире любой собранной строки: перенос по ширине экрана в этом тесте не проверяется

WORDS = ["ab", "x", "text", "  ", "1234", "Привет", "wide:日本"]
CODES = [
    "0",
    "1",
    "2",
    "3",
    "4",
    "7",
    "9",
    "22",
    "31",
    "42",
    "91",
    "103",
    "38;5;202",
    "48;5;17",
    "38;2;1;2;3",
    "39",
    "49",
]


def random_stream(seed: int) -> str:
    """
    Строки из слов, между которыми случайно стоят последовательности SGR, например ``ab<ESC>[1;31mtext<ESC>[0m``.
    """
    rng = random.Random(seed)
    lines = []
    for _ in range(rng.randint(1, 4)):
        parts = []
        for _ in range(rng.randint(1, 6)):
            if rng.random() < 0.6:
                parts.append(f"{ESC}[{';'.join(rng.sample(CODES, rng.randint(1, 3)))}m")
            parts.append(rng.choice(WORDS))
        lines.append("".join(parts))
    return "\r\n".join(lines) + "\r\n"


def cells(line: Line) -> list[tuple[str, Style]]:
    """
    Посимвольно: (символ, стиль); пробелы без оформления в конце строки не считаются (экран заполняет ими всю ширину).
    """
    result = [(char, span.style) for span in line.spans for char in span.text]
    while result and result[-1] == (" ", PLAIN):
        result.pop()
    return result


@pytest.mark.parametrize("seed", range(60), ids=lambda seed: f"seed-{seed}")
def test_pipe_parser_and_screen_emulator_give_the_same_cells(seed: int):
    stream = random_stream(seed)
    from_pipe = [cells(line) for line in parse(stream)]
    from_screen = [cells(line) for line in render(stream, columns=COLUMNS, rows=24)]
    assert from_pipe == from_screen, repr(stream)
