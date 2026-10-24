"""
От запуска команды до картинки: цвета вывода настоящего процесса доходят до пикселей.
"""

import sys

import pytest

pytest.importorskip("PIL")

from termsnap import run
from termsnap.errors import FontNotFound
from termsnap.png import render_image, resolve


def test_real_command_output_is_rendered_with_its_colours():
    try:
        fonts = resolve(covers="АЯабвёЖ")
    except FontNotFound as error:
        pytest.skip(f"в системе нет подходящего моноширинного шрифта: {error.problems}")
    capture = run([sys.executable, "-c", "print('\x1b[38;2;1;250;3mgreen\x1b[0m done')"])
    image = render_image(capture.lines, fonts=fonts, scale=2, font_size=28)
    colors = image.convert("RGB").getcolors(maxcolors=image.width * image.height) or []
    assert (1, 250, 3) in {color for _count, color in colors}
