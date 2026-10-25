"""
Чужие команды на близких к жизни сценариях: Node.js, git, pytest и ruff печатают цветной вывод, возврат каретки,
перерисовку строки и заголовки окна. Состав программ - ``tests/registry.py`` (записи с ``external=True``).

Вывод pytest и ruff зависит от их версий, поэтому ожидания записаны целиком, а версии зафиксированы: они стоят в
``uv.lock``, а ``pins.py`` сверяет их с установленными (``test_pins.py``). Вывод Node и git от версии не зависит
(сделаны оба вывода без трассировок, путей и ширины таблиц), поэтому их версии не фиксируются.
"""

import re

import pytest
from picture import check_snapshot_picture
from registry import REGISTRY, Program, require
from styles import styles_by_text
from support import require_module

from termsnap import Indexed, Line, PtyBackend, Rgb, Span, Style, run

NESTED = [program for program in REGISTRY if program.external]
NESTED_IDS = [program.name for program in NESTED]


def styled(lines: tuple[Line, ...]) -> bool:
    return any(
        span.style.fg is not None or span.style.bg is not None or span.style.bold or span.style.italic
        for line in lines
        for span in line.spans
    )


def texts(lines: tuple[Line, ...]) -> list[str]:
    return [line.text for line in lines]


def calm(text: str) -> str:
    """
    Убирает из строки то, что у одной и той же программы меняется от запуска к запуску и от системы к системе: время
    ("in 0.14s" в последней строке pytest) и длину линий из "=" и "_" (в Windows pytest пишет их на знак короче, чтобы
    не занимать последний столбец).
    """
    return re.sub(r"([=_])\1{3,}", r"\1\1\1\1", re.sub(r"in \d+\.\d+s", "in <time>", text))


@pytest.mark.parametrize("program", NESTED, ids=NESTED_IDS)
def test_program_output_is_clean_and_styled(program: Program, captures):
    capture = captures(program.name)
    assert (capture.returncode != 0) is program.expect_failure, capture.text
    assert capture.lines
    assert "\x1b" not in capture.text  # ни одна управляющая последовательность не просочилась в текст
    assert not any(char in capture.text for char in "\r\x07\x00")
    if program.colored:
        assert styled(capture.lines)


@pytest.mark.parametrize("program", NESTED, ids=NESTED_IDS)
def test_pipe_and_pty_give_the_same_text_and_styles(program: Program, captures):
    require_module("pyte")
    require(program)
    in_pty = run(program.argv, backend=PtyBackend(), timeout=60, **program.options)
    in_pipe = captures(program.name)
    assert [calm(line.text.rstrip()) for line in in_pty.lines] == [calm(line.text.rstrip()) for line in in_pipe.lines]
    assert in_pty.returncode == in_pipe.returncode


# --- Node.js: прогресс, перерисованный на месте, и заголовок окна ---

NODE_ANSI = [
    " " * 48,  # 48 клеток с фоном из палитры 256 цветов
    " " * 48,  # 48 клеток с фоном в 24-битном цвете
    "Готово",  # шкала из одиннадцати кадров перерисована на месте (возврат каретки), последний кадр стерт
    "жирный подчёркнутый красный курсив жёлтый серый ъяркие",
    "скрытый курсор",  # заголовок окна (OSC), скрытие и показ курсора в текст не попадают
]


def test_node_progress_is_overwritten_and_title_sequences_are_dropped(captures):
    capture = captures("node_ansi")
    assert texts(capture.lines) == NODE_ANSI


def test_node_backgrounds_keep_each_of_their_forty_eight_colours(captures):
    lines = captures("node_ansi").lines
    palette = [span.style.bg for span in lines[0].spans]
    truecolor = [span.style.bg for span in lines[1].spans]
    assert (len(palette), palette[0], palette[1], palette[-1]) == (48, Indexed(16), Indexed(20), Indexed(204))
    assert (len(truecolor), truecolor[0], truecolor[1], truecolor[-1]) == (
        48,
        Rgb(0, 255, 160),
        Rgb(5, 250, 160),
        Rgb(235, 20, 160),
    )


def test_node_text_attributes_and_bright_colours(captures):
    styles = {span.text.strip(): span.style for span in captures("node_ansi").lines[3].spans if span.text.strip()}
    assert styles == {
        "жирный подчёркнутый красный": Style(fg=Indexed(1), bold=True, underline=True),
        "курсив жёлтый": Style(fg=Indexed(3), italic=True),
        "серый": Style(fg=Indexed(8)),  # код 90 - яркий черный
        "ъяркие": Style(fg=Indexed(12), bg=Indexed(11)),  # коды 94 и 103
    }


# --- Node.js: util.inspect и console.log печатают значения цветами по их типам ---

NODE_INSPECT = [
    "{",  # console.log(data): Node красит вывод сам, когда вывод - терминал или FORCE_COLOR
    "  name: 'Хованов',",
    "  age: 21,",
    "  active: true,",
    "  nothing: null,",
    "  missing: undefined,",
    "  tags: [ 'a', 'b', 3, Symbol(s) ],",
    "  nested: { deep: { deeper: [Object] } },",  # глубже двух уровней Node сворачивает в [Object]
    "  fn: [Function: fn],",
    "  date: 1970-01-01T00:00:00.000Z,",
    "  map: Map(1) { 'k' => { v: 1 } },",
    "  big: 12345678901234567890n",
    "}",
    "{",  # util.inspect(data, { colors: true, depth: 0 }): вложенное свернуто сразу
    "  name: 'Хованов',",
    "  age: 21,",
    "  active: true,",
    "  nothing: null,",
    "  missing: undefined,",
    "  tags: [Array],",
    "  nested: [Object],",
    "  fn: [Function: fn],",
    "  date: 1970-01-01T00:00:00.000Z,",
    "  map: [Map],",
    "  big: 12345678901234567890n",
    "}",
    "строка=42 { x: 1 }",  # форматная строка: %s, %d, %o
    "[TypeError: что-то пошло не так]",  # ошибка без трассировки печатается в квадратных скобках
]

#: Цвета значений по их типам: строки зеленым, числа и логические жёлтым, null жирным, undefined серым, функции и
#: свернутое голубым, даты пурпурным. Тексты уникальны для типа, поэтому их можно искать по тексту.
NODE_INSPECT_STYLES = {
    "'Хованов'": Style(fg=Indexed(2)),
    "'a'": Style(fg=Indexed(2)),
    "3": Style(fg=Indexed(3)),
    "Symbol(s)": Style(fg=Indexed(2)),
    "21": Style(fg=Indexed(3)),
    "true": Style(fg=Indexed(3)),
    "null": Style(bold=True),
    "undefined": Style(fg=Indexed(8)),
    "[Array]": Style(fg=Indexed(6)),
    "[Object]": Style(fg=Indexed(6)),
    "[Function: fn]": Style(fg=Indexed(6)),
    "[Map]": Style(fg=Indexed(6)),
    "1970-01-01T00:00:00.000Z": Style(fg=Indexed(5)),
    "12345678901234567890n": Style(fg=Indexed(3)),
}


def test_node_inspect_prints_every_kind_of_value(captures):
    assert texts(captures("node_inspect").lines) == NODE_INSPECT


def test_node_inspect_colours_each_kind_of_value_differently(captures):
    assert NODE_INSPECT_STYLES.items() <= styles_by_text(captures("node_inspect")).items()


# --- git: граф истории с именами веток и тегами ---

GIT_LOG = [
    "*   8b23d16 (HEAD -> main, tag: v1) Merge feature",
    "|\\  ",
    "| * 4dab7c9 (feature) Draw the picture",
    "* | e05be3d Add the parser",
    "|/  ",
    "* c0314a5 Start the project",
]

YELLOW, CYAN, GREEN, RED = Indexed(3), Indexed(6), Indexed(2), Indexed(1)
PLAIN = Style()


def test_git_log_graph_has_the_merge_the_branch_and_the_tag(captures):
    assert texts(captures("git_log").lines) == GIT_LOG


def test_git_log_colours_hashes_names_and_graph_lines(captures):
    lines = captures("git_log").lines
    head = Style(fg=CYAN, bold=True)
    branch = Style(fg=GREEN, bold=True)
    around = (Span("*   ", PLAIN), Span("8b23d16 (", Style(fg=YELLOW)))
    after = (
        *(Span("main", branch), Span(", ", Style(fg=YELLOW))),
        *(Span("tag: v1", Style(fg=YELLOW, bold=True)), Span(")", Style(fg=YELLOW)), Span(" Merge feature", PLAIN)),
    )
    # старый git красит "HEAD -> " одним куском, новый - слово HEAD и стрелку по отдельности (проверены 2.39 и 2.55)
    joined = (*around, Span("HEAD -> ", head), *after)
    split = (*around, Span("HEAD", head), Span(" -> ", Style(fg=YELLOW)), *after)
    assert lines[0].spans in (joined, split)
    assert lines[1].spans == (Span("|", Style(fg=RED)), Span("\\", Style(fg=GREEN)), Span("  ", PLAIN))
    assert lines[2].spans[-3:] == (  # ветка без HEAD: имя зеленым жирным в скобках цвета хеша
        Span("feature", branch),
        Span(")", Style(fg=YELLOW)),
        Span(" Draw the picture", PLAIN),
    )


# --- pytest: отчет о падении ---

PYTEST_FAILURE = [
    ".FF                                                                                          [100%]",
    "==== FAILURES ====",
    "____ test_list_diff ____",
    "",
    "    def test_list_diff():",
    "        expected = [1, 2, 3]",
    "        actual = [1, 2, 4]",
    ">       assert actual == expected",
    "E       assert [1, 2, 4] == [1, 2, 3]",
    "E         ",
    "E         At index 2 diff: 4 != 3",
    "E         Use -v to get more diff",
    "",
    "failing_cases.py:8: AssertionError",
    "____ test_text ____",
    "",
    "    def test_text():",
    '>       assert "термин" in "словарь"',
    "E       AssertionError: assert 'термин' in 'словарь'",
    "",
    "failing_cases.py:12: AssertionError",
    "==== short test summary info ====",
    "FAILED failing_cases.py::test_list_diff - assert [1, 2, 4] == [1, 2, 3]",
    "FAILED failing_cases.py::test_text - AssertionError: assert 'термин' in 'словарь'",
    "2 failed, 1 passed in <time>",
]


def test_pytest_failure_report(captures):
    capture = captures("pytest_failure")
    assert [calm(line.text) for line in capture.lines] == PYTEST_FAILURE


def test_pytest_failure_report_colours(captures):
    lines = captures("pytest_failure").lines
    assert lines[0].spans == (Span(".", Style(fg=GREEN)), Span("FF" + " " * 90 + "[100%]", Style(fg=RED)))
    assert [span.style for span in lines[2].spans] == [Style(fg=RED, bold=True)]  # заголовок упавшего теста
    assert lines[4].spans == (  # исходный текст теста подсвечен как код Python
        Span("    ", PLAIN),
        Span("def", Style(fg=Indexed(12))),
        Span(" ", Style(fg=Indexed(8))),
        Span("test_list_diff", Style(fg=Indexed(10))),
        Span("():", PLAIN),
    )
    assert lines[6].spans[2:4] == (Span(", ", PLAIN), Span("2", Style(fg=Indexed(12))))  # числа в коде подсвечены
    assert lines[8].spans == (Span(lines[8].text, Style(fg=RED, bold=True)),)  # строка с ошибкой
    assert [(span.text, span.style) for span in lines[-1].spans] == [
        ("2 failed", Style(fg=RED, bold=True)),
        (", ", PLAIN),
        ("1 passed", Style(fg=GREEN)),
        (lines[-1].spans[-1].text, Style(fg=RED)),  # " in 0.14s": время красным, потому что есть падения
    ]


# --- ruff: диагностика с подчеркнутыми местами и предложенными исправлениями ---

RUFF_DIAGNOSTICS = """\
E401 [*] Multiple imports on one line
 --> bad_style.py:1:1
  |
1 | import os, sys
  | ^^^^^^^^^^^^^^
2 | def f( x ):
3 |     unused = 1
  |
help: Split imports
  |
  - import os, sys
1 + import os
2 + import sys
3 | def f( x ):
  |

I001 [*] Import block is un-sorted or un-formatted
 --> bad_style.py:1:1
  |
1 | import os, sys
  | ^^^^^^^^^^^^^^
2 | def f( x ):
3 |     unused = 1
  |
help: Organize imports
  |
  - import os, sys
1 + import os
2 + import sys
3 +
4 +
5 | def f( x ):
  |

F401 [*] `os` imported but unused
 --> bad_style.py:1:8
  |
1 | import os, sys
  |        ^^
2 | def f( x ):
3 |     unused = 1
  |
help: Remove unused import
  |
  - import os, sys
1 | def f( x ):
  |

F401 [*] `sys` imported but unused
 --> bad_style.py:1:12
  |
1 | import os, sys
  |            ^^^
2 | def f( x ):
3 |     unused = 1
  |
help: Remove unused import
  |
  - import os, sys
1 | def f( x ):
  |

F841 Local variable `unused` is assigned to but never used
 --> bad_style.py:3:5
  |
1 | import os, sys
2 | def f( x ):
3 |     unused = 1
  |     ^^^^^^
4 |     return x+1
5 | print( f(2) )
  |
help: Remove assignment to unused variable `unused`
  |
2 | def f( x ):
  -     unused = 1
3 |     return x+1
  |
note: This is an unsafe fix and may change runtime behavior

Found 5 errors.
[*] 4 fixable with `--fix` (1 unsafe fix available with `--fix --unsafe-fixes`).
""".splitlines()


def test_ruff_diagnostics_report(captures):
    assert texts(captures("ruff_diagnostics").lines) == RUFF_DIAGNOSTICS


def test_ruff_diagnostics_colours(captures):
    capture = captures("ruff_diagnostics")
    assert capture.lines[0].spans == (
        Span("E401", Style(fg=Indexed(9), bold=True)),  # код правила
        Span(" [", PLAIN),
        Span("*", Style(fg=Indexed(14), bold=True)),  # у нарушения есть автоматическое исправление
        Span("]", PLAIN),
        Span(" Multiple imports on one line", Style(bold=True)),
    )
    assert capture.lines[4].spans == (
        Span("  ", PLAIN),
        Span("|", Style(fg=Indexed(12), bold=True)),
        Span(" ", PLAIN),
        Span("^" * 14, Style(fg=Indexed(9), bold=True)),  # подчеркнутое место
    )
    removed, added = capture.lines[10], capture.lines[11]
    assert removed.spans[-3:] == (  # удаляемое красным, внутри жирным то, что именно меняется
        Span("import ", Style(fg=Indexed(1))),
        Span("os,", Style(fg=Indexed(1), bold=True)),
        Span(" sys", Style(fg=Indexed(1))),
    )
    assert added.spans[-2:] == (Span("import ", Style(fg=Indexed(2))), Span("os", Style(fg=Indexed(2), bold=True)))


# --- PNG ---


@pytest.mark.parametrize("program", NESTED, ids=NESTED_IDS)
def test_program_renders_to_a_picture_that_follows_its_screen(program: Program, captures, bundled_fonts):
    check_snapshot_picture(captures(program.name).lines, bundled_fonts)
