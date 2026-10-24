"""
Вывод программы -> строки со стилями, какими они оказались на экране.
"""

import pyte

from termsnap.model import Line
from termsnap.screen.convert import line_of
from termsnap.screen.emulator import TerminalScreen

#: Сколько строк, ушедших вверх за пределы экрана, помнит эмулятор. С запасом: длинный вывод не должен обрезаться.
HISTORY_LINES = 100_000


def render(text: str, *, columns: int, rows: int, visible_only: bool = False) -> tuple[Line, ...]:
    """
    Строки со стилями, которые остались на экране ``columns`` x ``rows`` после вывода ``text``. По умолчанию
    вместе со строками, ушедшими вверх при прокрутке (так не теряется длинный вывод); с ``visible_only`` - только
    то, что видно на экране сейчас, как на скриншоте окна терминала. Пустые строки в конце отбрасываются.
    """
    screen = TerminalScreen(columns, rows, history=HISTORY_LINES)
    pyte.Stream(screen).feed(text)
    # итог = [строки, ушедшие вверх] + [строки на экране], а пустой хвост убираем
    scrolled_off = [] if visible_only else screen.history.top
    stored = [[row[column] for column in range(columns)] for row in scrolled_off]
    visible = [[screen.buffer[y][column] for column in range(columns)] for y in range(rows)]
    lines = [line_of(cells) for cells in stored + visible]
    while lines and not lines[-1].spans:
        lines.pop()
    return tuple(lines)
