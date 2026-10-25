"""
Скрипты rich из ``tests/programs`` запускаются в канале: нетривиальный цветной вывод, возврат каретки, перерисовка
строк, эмодзи, иероглифы и псевдографика. Ожидаемый вывод каждой программы записан здесь же целиком, чтобы тест можно
было прочитать без самой программы. Чужие команды (node, pytest, ruff, git) проверяются в ``tests/external``.

Версии rich держит ``uv.lock``: вывод программ от них зависит, поэтому после обновления rich ожидания надо сверить.
"""

import io

import pytest
from registry import REGISTRY, Program
from styles import rstripped, styles_by_text

from termsnap import Indexed, Line, Rgb, Style

VS16 = "\N{VARIATION SELECTOR-16}"  # селектор эмодзи: символ перед ним рисуется как цветной эмодзи в две клетки

PROJECT = [program for program in REGISTRY if not program.external]


def styled(lines: tuple[Line, ...]) -> bool:
    return any(
        span.style.fg is not None or span.style.bg is not None or span.style.bold or span.style.italic
        for line in lines
        for span in line.spans
    )


@pytest.mark.parametrize("program", PROJECT, ids=lambda program: program.name)
def test_program_output_is_clean_and_styled(program: Program, captures):
    capture = captures(program.name)
    assert (capture.returncode != 0) is program.expect_failure, capture.text
    assert capture.lines
    assert "\x1b" not in capture.text  # ни одна управляющая последовательность не просочилась в текст
    assert not any(char in capture.text for char in "\r\x07\x00")
    if program.colored:
        assert styled(capture.lines)


# --- rich_table: таблица с эмодзи, цветами столбцов и подписями ---

RICH_TABLE = [
    "            Результаты испытаний             ",
    "╭───┬─────────────────┬──────────┬──────────╮",
    "│ № │ Название        │  Статус  │ Время, с │",
    "├───┼─────────────────┼──────────┼──────────┤",
    "│ 1 │ Загрузка данных │    OK    │     0.42 │",
    "├───┼─────────────────┼──────────┼──────────┤",
    "│ 2 │ Обучение модели │ медленно │    12.80 │",
    "├───┼─────────────────┼──────────┼──────────┤",
    "│ 3 │ Проверка 🚀     │ ошибка ✗ │     3.05 │",  # эмодзи занимает две клетки: рамка не сдвигается
    "├───┼─────────────────┼──────────┼──────────┤",
    "│ 4 │ Отчёт ✅        │  готово  │     0.07 │",
    "╰───┴─────────────────┴──────────┴──────────╯",
    "               Данные условные               ",
]

#: Столбцы: № - бирюзовый, название - жирный пурпурный, время - зеленый; статус красится прямо в тексте ячейки.
RICH_TABLE_STYLES = {
    "Результаты испытаний": Style(italic=True),
    "№": Style(bold=True),
    "Название": Style(bold=True),
    "1": Style(fg=Indexed(6)),
    "Загрузка данных": Style(fg=Indexed(5), bold=True),
    "OK": Style(fg=Indexed(2)),
    "медленно": Style(fg=Indexed(3)),
    "ошибка ✗": Style(fg=Indexed(1)),
    "готово": Style(fg=Indexed(2)),
    "12.80": Style(fg=Indexed(2)),
    "3.05": Style(fg=Indexed(2), bold=True),  # жирный внутри ячейки поверх цвета столбца
    "Данные условные": Style(dim=True, italic=True),
}


def test_rich_table_is_drawn_exactly_and_its_frame_is_a_rectangle_even_with_emoji(captures):
    capture = captures("rich_table")
    assert [line.text for line in capture.lines] == RICH_TABLE
    assert {line.width for line in capture.lines[1:12]} == {45}  # все строки рамки одной ширины в клетках


def test_rich_table_cells_have_the_styles_of_their_columns(captures):
    assert RICH_TABLE_STYLES.items() <= styles_by_text(captures("rich_table")).items()


# --- rich_panel_tree: дерево в панели и панель по размеру текста ---

RICH_PANEL_TREE = [
    "╭─────────────────────── Структура ────────────────────────╮",
    "│                                                          │",
    "│  📁 проект                                               │",
    "│  ├── 📁 src                                              │",
    "│  │   ├── 🐍 main.py                                      │",
    "│  │   └── 🐍 utils.py                                     │",
    "│  ├── 📁 docs                                             │",
    "│  │   ├── 📄 README.md                                    │",
    "│  │   └── 🖼  схема.png                                    │",
    "│  └── 🔒 .env                                             │",
    "│                                                          │",
    "╰─────────────────────── 3 каталога ───────────────────────╯",
    "╭────────────────────────────────╮",
    "│  ВНИМАНИЕ  Проверьте настройки │",
    "╰────────────────────────────────╯",
]


def test_rich_panel_and_tree_are_drawn_exactly_with_straight_borders(captures):
    capture = captures("rich_panel_tree")
    assert [line.text for line in capture.lines] == RICH_PANEL_TREE
    assert {line.width for line in capture.lines[:12]} == {60}  # большая панель: ширина задана программой
    assert {line.width for line in capture.lines[12:]} == {34}  # малая подгоняется под текст


def test_rich_panel_tree_has_coloured_names_and_a_warning_on_red(captures):
    styles = styles_by_text(captures("rich_panel_tree"))
    assert styles["Структура"] == Style(fg=Indexed(12), bold=True)
    assert styles["проект"] == Style(fg=Indexed(4), bold=True)
    assert styles["main.py"] == Style(fg=Indexed(2))
    assert styles["README.md"] == Style(dim=True)
    assert styles["ВНИМАНИЕ"] == Style(fg=Indexed(7), bg=Indexed(1), bold=True)


# --- rich_progress и rich_live: перерисовка на месте оставляет только последний кадр ---


def test_rich_progress_shows_only_the_final_state_not_every_frame(captures):
    capture = captures("rich_progress")
    assert [line.text for line in capture.lines] == [
        "Скачивание ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 40/40",
        "Обработка  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 40/40",
        "Готово",
    ]
    styles = styles_by_text(capture)
    assert styles["Скачивание"] == Style(fg=Indexed(4), bold=True)
    assert styles["100%"] == Style(fg=Indexed(5))
    assert styles["40/40"] == Style(fg=Indexed(2))


def test_rich_live_shows_one_table_not_every_frame(captures):
    assert [line.text for line in captures("rich_live").lines] == [
        "        Шаг 5        ",
        "┏━━━━━━━━┳━━━━━━━━━━┓",
        "┃ Узел   ┃ Нагрузка ┃",
        "┡━━━━━━━━╇━━━━━━━━━━┩",
        "│ node-0 │      35% │",
        "│ node-1 │      48% │",
        "│ node-2 │      61% │",
        "└────────┴──────────┘",
        "Итог: пять обновлений",
    ]


# --- rich_syntax: подсветка кода с номерами строк на фоне ---

RICH_SYNTAX = [
    "   1 from dataclasses import dataclass",
    "   2",
    "   3",
    "   4 @dataclass(frozen=True, slots=True)",
    "   5 class Point:",
    "   6     x: float",
    "   7     y: float",
    "   8",
    '   9     def distance(self, other: "Point") -> float:',
    '  10         """Расстояние до другой точки."""',
    "  11         return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5",
    "  12",
    "  13",
    "  14 print(Point(0, 0).distance(Point(3, 4)))  # 5.0",
    "  15",
    "from dataclasses import dataclass",  # второй блок: без номеров, на другом фоне
    "x = [i for i in range(10)]",
]


def test_rich_syntax_is_numbered_highlighted_and_on_a_background(captures):
    capture = captures("rich_syntax")
    assert rstripped(capture) == RICH_SYNTAX
    styles = styles_by_text(capture)
    assert styles["def"] == Style(fg=Indexed(81), bg=Indexed(235))  # ключевое слово на фоне темы monokai
    assert styles["return"] == Style(fg=Indexed(81), bg=Indexed(235))
    assert {span.style.bg for span in capture.lines[15].spans} == {Indexed(255)}  # второй блок на светлом фоне


# --- rich_markdown ---

RICH_MARKDOWN = [
    "             Заголовок первого уровня",
    "",
    "Обычный абзац с жирным, курсивом, кодом и ссылкой.",
    "",
    "Список",
    "",
    " • первый пункт",
    " • второй пункт",
    "    • вложенный пункт",
    "",
    " 1 нумерованный",
    " 2 список",
    "",
    "▌ Цитата, которая занимает несколько слов.",
    "",
    "",
    " def hello(name: str) -> str:",
    '     return f"Привет, {name}!"',
    "",
    "",
    "-" * 50,
    "",
]


def test_rich_markdown_has_headings_lists_quote_code_and_a_rule(captures):
    capture = captures("rich_markdown")
    assert rstripped(capture) == RICH_MARKDOWN
    styles = styles_by_text(capture)
    assert styles["Заголовок первого уровня"] == Style(bold=True, underline=True)
    assert styles["жирным"] == Style(bold=True)
    assert styles["курсивом"] == Style(italic=True)
    assert styles["кодом"] == Style(fg=Indexed(6), bg=Indexed(0), bold=True)
    assert styles["ссылкой"] == Style(fg=Indexed(4), underline=True)
    assert styles["def"].bg == Indexed(235)  # блок кода на своем фоне


# --- rich_misc: градиент, атрибуты, гиперссылка, колонки, эмодзи и иероглифы ---

RICH_MISC = [
    "───────────────────────────────────────── Градиент и стили ─────────────────────────────────────────",
    "█" * 60,
    "жирный курсив подчёркнутый зачёркнутый тусклый обратный",
    "ссылка с гиперссылкой OSC 8 и  фон",  # сама ссылка (OSC 8) в текст не попадает
    "─" * 100,
    "альфа            бета          гамма           дельта             эпсилон              дзета",
    f"Эмодзи: 🚀 ✅ ❌ ⚠{VS16} 🐍  Иероглифы: 日本語 中文  Рамки: ┌─┬─┐│ │ │└─┴─┘",
]


def test_rich_misc_text_is_drawn_exactly(captures):
    assert rstripped(captures("rich_misc")) == RICH_MISC


def test_rich_gradient_keeps_each_of_its_sixty_truecolor_steps(captures):
    gradient = captures("rich_misc").lines[1]
    colours = [span.style.fg for span in gradient.spans]
    assert len(colours) == 60
    assert colours[0] == Rgb(255, 0, 128)  # шаг 0: красный максимален, зеленый минимален
    assert colours[1] == Rgb(251, 4, 128)
    assert colours[-1] == Rgb(19, 236, 128)  # шаг 59: 255 - 59 * 4 и 59 * 4


def test_rich_misc_attributes_are_each_on_their_own_word(captures):
    styles = styles_by_text(captures("rich_misc"))
    assert styles["жирный"] == Style(bold=True)
    assert styles["курсив"] == Style(italic=True)
    assert styles["подчёркнутый"] == Style(underline=True)
    assert styles["зачёркнутый"] == Style(strike=True)
    assert styles["тусклый"] == Style(dim=True)
    assert styles["обратный"] == Style(inverse=True)
    assert styles["фон"] == Style(bg=Indexed(4))


def test_rich_traceback_shows_the_error_and_the_failing_line(captures):
    # пути к файлам зависят от машины, поэтому строка с ошибкой и код проверяются по тексту
    lines = [line.text.rstrip() for line in captures("rich_traceback").lines]
    assert "ZeroDivisionError: division by zero" in lines
    assert any("❱  5 │   return a / b" in line for line in lines)  # стрелка указывает на строку, где упало


# - картинки -
@pytest.mark.parametrize("program", PROJECT, ids=lambda program: program.name)
def test_every_program_renders_to_png(program: Program, captures):
    pytest.importorskip("PIL")
    from PIL import Image

    from termsnap.errors import FontNotFound
    from termsnap.png import render_png

    try:
        data = render_png(captures(program.name).lines, font_size=12, scale=1)
    except FontNotFound as error:
        pytest.skip(f"нет моноширинного шрифта: {error.problems}")
    image = Image.open(io.BytesIO(data))
    assert image.width > 100
    assert image.height > 10
