"""
От запуска команды до картинки: цвета вывода настоящего процесса доходят до пикселей.
"""

import sys

from support import require_module

require_module("PIL")

from termsnap import run
from termsnap.png import render_image


def test_real_command_output_is_rendered_with_its_colours(system_fonts):
    fonts = system_fonts
    capture = run([sys.executable, "-c", "print('\x1b[38;2;1;250;3mgreen\x1b[0m done')"])
    image = render_image(capture.lines, fonts=fonts, scale=2, font_size=28)
    colors = image.convert("RGB").getcolors(maxcolors=image.width * image.height) or []
    assert (1, 250, 3) in {color for _count, color in colors}
