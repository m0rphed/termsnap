"""
Скрипты rich из ``tests/programs`` запускаются в канале: нетривиальный цветной вывод, возврат каретки, перерисовка
строк, эмодзи, иероглифы и псевдографика. Ожидаемый вывод каждой программы записан здесь же целиком, чтобы тест можно
было прочитать без самой программы. Чужие команды (node, pytest, ruff, git) проверяются в ``tests/external``.

Версии rich держит ``uv.lock``: вывод программ от них зависит, поэтому после обновления rich ожидания надо сверить.
"""

import pytest
from helpers import VS16, texts
from picture import check_snapshot_picture
from registry import REGISTRY, Program
from styles import control_characters, rstripped, styled, styles_by_text

from termsnap import Indexed, Rgb, Style

PROJECT = [program for program in REGISTRY if not program.external]


@pytest.mark.parametrize("program", PROJECT, ids=lambda program: program.name)
def test_program_prints_something(program: Program, captures):
    assert captures(program.name).lines


@pytest.mark.parametrize("program", PROJECT, ids=lambda program: program.name)
def test_program_exit_code_is_the_expected_one(program: Program, captures):
    capture = captures(program.name)
    assert (capture.returncode != 0) is program.expect_failure, capture.text


@pytest.mark.parametrize("program", PROJECT, ids=lambda program: program.name)
def test_program_text_has_no_control_characters(program: Program, captures):
    # ни одна управляющая последовательность не просочилась в текст
    assert control_characters(captures(program.name).text) == []


@pytest.mark.parametrize("program", [item for item in PROJECT if item.colored], ids=lambda item: item.name)
def test_program_output_has_colours_or_attributes(program: Program, captures):
    assert styled(captures(program.name).lines)


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


def test_rich_table_is_drawn_exactly(captures):
    assert texts(captures("rich_table")) == RICH_TABLE


def test_rich_table_frame_is_a_rectangle_even_with_emoji(captures):
    assert {line.width for line in captures("rich_table").lines[1:12]} == {45}  # одна ширина в клетках


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


def test_rich_panel_and_tree_are_drawn_exactly(captures):
    assert texts(captures("rich_panel_tree")) == RICH_PANEL_TREE


def test_rich_panels_have_straight_borders_of_their_own_widths(captures):
    lines = captures("rich_panel_tree").lines
    assert {line.width for line in lines[:12]} == {60}  # большая панель: ширина задана программой
    assert {line.width for line in lines[12:]} == {34}  # малая подгоняется под текст


def test_rich_panel_tree_has_coloured_names_and_a_warning_on_red(captures):
    assert (
        styles_by_text(captures("rich_panel_tree")).items()
        >= {
            "Структура": Style(fg=Indexed(12), bold=True),
            "проект": Style(fg=Indexed(4), bold=True),
            "main.py": Style(fg=Indexed(2)),
            "README.md": Style(dim=True),
            "ВНИМАНИЕ": Style(fg=Indexed(7), bg=Indexed(1), bold=True),
        }.items()
    )


# --- rich_progress и rich_live: перерисовка на месте оставляет только последний кадр ---


def test_rich_progress_shows_only_the_final_state_not_every_frame(captures):
    assert texts(captures("rich_progress")) == [
        "Скачивание ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 40/40",
        "Обработка  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 40/40",
        "Готово",
    ]


def test_rich_progress_columns_have_their_colours(captures):
    assert (
        styles_by_text(captures("rich_progress")).items()
        >= {
            "Скачивание": Style(fg=Indexed(4), bold=True),
            "100%": Style(fg=Indexed(5)),
            "40/40": Style(fg=Indexed(2)),
        }.items()
    )


def test_rich_live_shows_one_table_not_every_frame(captures):
    assert texts(captures("rich_live")) == [
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


def test_rich_syntax_is_drawn_with_numbers(captures):
    assert rstripped(captures("rich_syntax")) == RICH_SYNTAX


def test_rich_syntax_highlights_keywords_on_the_background_of_the_theme(captures):
    assert (
        styles_by_text(captures("rich_syntax")).items()
        >= {  # ключевые слова на фоне темы monokai
            "def": Style(fg=Indexed(81), bg=Indexed(235)),
            "return": Style(fg=Indexed(81), bg=Indexed(235)),
        }.items()
    )


def test_rich_syntax_second_block_is_on_a_light_background(captures):
    assert {span.style.bg for span in captures("rich_syntax").lines[15].spans} == {Indexed(255)}


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
    assert rstripped(captures("rich_markdown")) == RICH_MARKDOWN


def test_rich_markdown_inline_styles_and_code_block(captures):
    styles = styles_by_text(captures("rich_markdown"))
    assert (
        styles.items()
        >= {
            "Заголовок первого уровня": Style(bold=True, underline=True),
            "жирным": Style(bold=True),
            "курсивом": Style(italic=True),
            "кодом": Style(fg=Indexed(6), bg=Indexed(0), bold=True),
            "ссылкой": Style(fg=Indexed(4), underline=True),
        }.items()
    )
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
    # шаг 0: красный максимален, зеленый минимален; шаг 59: 255 - 59 * 4 и 59 * 4
    assert (colours[0], colours[1], colours[-1]) == (Rgb(255, 0, 128), Rgb(251, 4, 128), Rgb(19, 236, 128))


def test_rich_misc_attributes_are_each_on_their_own_word(captures):
    assert (
        styles_by_text(captures("rich_misc")).items()
        >= {
            "жирный": Style(bold=True),
            "курсив": Style(italic=True),
            "подчёркнутый": Style(underline=True),
            "зачёркнутый": Style(strike=True),
            "тусклый": Style(dim=True),
            "обратный": Style(inverse=True),
            "фон": Style(bg=Indexed(4)),
        }.items()
    )


def test_rich_traceback_shows_the_error_and_the_failing_line(captures):
    # пути к файлам зависят от машины, поэтому строка с ошибкой и код проверяются по тексту
    lines = rstripped(captures("rich_traceback"))
    assert "ZeroDivisionError: division by zero" in lines
    assert any("❱  5 │   return a / b" in line for line in lines)  # стрелка указывает на строку, где упало


# - картинки -
@pytest.mark.parametrize("program", PROJECT, ids=lambda program: program.name)
def test_every_program_renders_to_a_picture_that_follows_its_screen(program: Program, captures, bundled_fonts):
    check_snapshot_picture(captures(program.name).lines, bundled_fonts)
