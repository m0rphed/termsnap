"""
Окружение процесса "как у терминала": размер и тип терминала, UTF-8, принудительный цвет или его отсутствие.
"""

import pytest

from termsnap import terminal_environment

BASE = {"PATH": "/bin", "KEEP": "yes"}


def environment(base=BASE, **options):
    return terminal_environment(base, **{"color": True, "columns": 100, "rows": 30, **options})


def test_terminal_type_and_size_are_announced():
    env = environment(columns=80, rows=24)
    assert (env["TERM"], env["COLUMNS"], env["LINES"]) == ("xterm-256color", "80", "24")


def test_another_terminal_type_can_be_announced():
    assert environment(term="vt100")["TERM"] == "vt100"


def test_python_is_told_to_use_utf8():
    env = environment()
    assert (env["PYTHONUTF8"], env["PYTHONIOENCODING"]) == ("1", "utf-8")


def test_color_on_forces_color_for_programs_that_check_the_variables():
    env = environment(color=True)
    assert (env["FORCE_COLOR"], env["CLICOLOR_FORCE"]) == ("1", "1")
    assert "NO_COLOR" not in env


def test_color_off_sets_no_color_and_no_force_variables():
    env = environment(color=False)
    assert env["NO_COLOR"] == "1"
    assert "FORCE_COLOR" not in env
    assert "CLICOLOR_FORCE" not in env


@pytest.mark.parametrize("color", [True, False])
def test_color_variables_of_the_base_environment_never_decide_the_color(color: bool):
    base = {"NO_COLOR": "1", "FORCE_COLOR": "0", "CLICOLOR_FORCE": "0"}
    env = environment(base, color=color)
    assert (env.get("NO_COLOR") == "1") is (not color)
    assert (env.get("FORCE_COLOR") == "1") is color
    assert (env.get("CLICOLOR_FORCE") == "1") is color


def test_other_variables_of_the_base_environment_are_kept():
    assert environment()["KEEP"] == "yes"
    assert environment()["PATH"] == "/bin"


def test_terminal_variables_replace_the_ones_of_the_base_environment():
    env = environment({"TERM": "dumb", "COLUMNS": "5", "LINES": "5"})
    assert (env["TERM"], env["COLUMNS"], env["LINES"]) == ("xterm-256color", "100", "30")


def test_the_base_environment_is_not_modified():
    base = {"NO_COLOR": "1"}
    environment(base)
    assert base == {"NO_COLOR": "1"}
