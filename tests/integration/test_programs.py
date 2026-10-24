"""
Проверки на скриптах проекта (rich): нетривиальный цветной вывод, возврат каретки, перерисовка строк, эмодзи, иероглифы
и псевдографика. Состав программ - ``examples/registry.py``. Чужие команды (node, pytest, ruff, git) - в ``external``.
"""

import io

import pytest
from registry import REGISTRY, Program

from termsnap import Line

BOX_START = set("╭│├╰┏┃┡┗┌└┐┘┤┬┴┼")


def styled(lines: tuple[Line, ...]) -> bool:
    return any(
        span.style.fg is not None or span.style.bg is not None or span.style.bold or span.style.italic
        for line in lines
        for span in line.spans
    )


def box_runs(lines: tuple[Line, ...]) -> list[list[Line]]:
    """
    Подряд идущие строки, которые начинаются с символа рамки: это одна рамка (таблица, панель).
    """
    runs: list[list[Line]] = []
    current: list[Line] = []
    for line in lines:
        if line.text[:1] in BOX_START:
            if current and line.text[:1] == "╭":  # верхний край следующей рамки без пустой строки между ними
                runs.append(current)
                current = []
            current.append(line)
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


PROJECT = [program for program in REGISTRY if not program.external]


@pytest.mark.parametrize("program", PROJECT, ids=lambda program: program.name)
def test_program_output_is_clean_and_styled(program: Program, captures):
    capture = captures(program.name)
    assert (capture.returncode != 0) is program.expect_failure, capture.text
    assert capture.lines
    assert "\x1b" not in capture.text  # ни одна управляющая последовательность не просочилась в текст
    assert not any(char in capture.text for char in "\r\x07\x00")
    if program.colored:
        assert styled(capture.lines)


@pytest.mark.parametrize("name", [p.name for p in PROJECT if p.name.startswith("rich_")])
def test_rich_output_fits_the_requested_width(name: str, captures):
    assert max(line.width for line in captures(name).lines) <= 100


def test_rich_boxes_are_rectangles_even_with_emoji(captures):
    for name in ("rich_table", "rich_panel_tree"):
        runs = box_runs(captures(name).lines)
        assert runs
        for run_lines in runs:
            assert len({line.width for line in run_lines}) == 1, (name, [line.text for line in run_lines])


def test_rich_table_keeps_emoji_and_colours(captures):
    capture = captures("rich_table")
    assert "🚀" in capture.text
    assert "✅" in capture.text
    colours = {span.style.fg for line in capture.lines for span in line.spans if span.style.fg is not None}
    assert len(colours) >= 4


def test_rich_progress_shows_only_final_state(captures):
    lines = captures("rich_progress").lines
    assert len(lines) == 3
    assert lines[0].text.startswith("Скачивание")
    assert "100%" in lines[0].text
    assert "100%" in lines[1].text
    assert lines[2].text == "Готово"


def test_rich_live_shows_one_table_not_every_frame(captures):
    lines = captures("rich_live").lines
    assert sum("Нагрузка" in line.text for line in lines) == 1
    assert sum("Шаг" in line.text for line in lines) == 1
    assert "Шаг 5" in "\n".join(line.text for line in lines)
    assert lines[-1].text == "Итог: пять обновлений"


def test_rich_gradient_is_truecolor(captures):
    from termsnap import Rgb

    colours = {span.style.fg for line in captures("rich_misc").lines for span in line.spans}
    assert sum(isinstance(colour, Rgb) for colour in colours) >= 20


def test_rich_syntax_has_background_and_line_numbers(captures):
    lines = captures("rich_syntax").lines
    assert lines[0].text.lstrip().startswith("1 from dataclasses")
    assert any(span.style.bg is not None for line in lines for span in line.spans)


def test_rich_traceback_shows_the_error_and_marks_the_line(captures):
    text = captures("rich_traceback").text
    assert "ZeroDivisionError: division by zero" in text
    assert "return a / b" in text


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
