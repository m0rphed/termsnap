"""
Чужие команды на близких к жизни сценариях: Node.js, pytest, ruff и git печатают цветной вывод, возврат каретки,
перерисовку строки и заголовки окна. Состав программ - ``examples/registry.py`` (записи с ``external=True``).
"""

import io
import sys

import pytest
from registry import REGISTRY, Program

from termsnap import Line, run

NESTED = [program for program in REGISTRY if program.external]


def styled(lines: tuple[Line, ...]) -> bool:
    return any(
        span.style.fg is not None or span.style.bg is not None or span.style.bold or span.style.italic
        for line in lines
        for span in line.spans
    )


@pytest.mark.parametrize("program", NESTED, ids=lambda program: program.name)
def test_program_output_is_clean_and_styled(program: Program, captures):
    capture = captures(program.name)
    assert (capture.returncode != 0) is program.expect_failure, capture.text
    assert capture.lines
    assert "\x1b" not in capture.text  # ни одна управляющая последовательность не просочилась в текст
    assert not any(char in capture.text for char in "\r\x07\x00")
    if program.colored:
        assert styled(capture.lines)


def test_node_progress_is_overwritten_and_title_sequences_are_dropped(captures):
    text = captures("node_ansi").text
    assert "Готово" in text
    assert "[#" not in text
    assert "заголовок окна" not in text
    assert "скрытый курсор" in text


def test_node_inspect_has_coloured_values(captures):
    capture = captures("node_inspect")
    assert "Хованов" in capture.text
    assert "(index)" in capture.text
    assert "TypeError: что-то пошло не так" in capture.text
    colours = {span.style.fg for line in capture.lines for span in line.spans if span.style.fg is not None}
    assert len(colours) >= 3


def test_pytest_failure_report(captures):
    capture = captures("pytest_failure")
    assert "2 failed, 1 passed" in capture.text
    assert "AssertionError" in capture.text
    assert any(span.style.fg is not None and span.style.bold for line in capture.lines for span in line.spans)


def test_ruff_diagnostics(captures):
    text = captures("ruff_diagnostics").text
    assert "E401" in text
    assert "bad_style.py" in text


@pytest.mark.parametrize("program", NESTED, ids=lambda program: program.name)
def test_program_renders_to_png(program: Program, captures):
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


@pytest.mark.parametrize("program", NESTED, ids=lambda program: program.name)
def test_program_runs_in_a_pty_and_leaves_no_escape_sequences(program: Program):
    pytest.importorskip("pyte")
    if sys.platform == "win32":
        pytest.importorskip("winpty")
    from termsnap import PtyBackend

    if not program.available:
        pytest.skip(f"нет программы {program.tool}")
    capture = run(program.argv, backend=PtyBackend(), timeout=60)
    assert (capture.returncode != 0) is program.expect_failure, program.name
    assert capture.lines, program.name
    assert "\x1b" not in capture.text, program.name


def test_node_progress_looks_the_same_in_a_pipe_and_in_a_pty(captures):
    pytest.importorskip("pyte")
    if sys.platform == "win32":
        pytest.importorskip("winpty")
    from termsnap import PtyBackend

    if not next(p for p in NESTED if p.name == "node_ansi").available:
        pytest.skip("нет программы node")
    in_pty = run(next(p for p in NESTED if p.name == "node_ansi").argv, backend=PtyBackend(), timeout=60)
    assert [line.text.rstrip() for line in in_pty.lines] == [line.text.rstrip() for line in captures("node_ansi").lines]
