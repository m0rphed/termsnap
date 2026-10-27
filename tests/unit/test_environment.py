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


def test_extra_variables_are_added_and_the_rest_of_the_base_environment_stays():
    env = environment(extra={"ADDED": "1"})
    assert (env["ADDED"], env["KEEP"], env["PATH"]) == ("1", "yes", "/bin")


def test_extra_variables_replace_the_ones_of_the_base_environment():
    assert environment(extra={"KEEP": "no"})["KEEP"] == "no"


def test_extra_variables_may_be_empty_strings():
    assert environment(extra={"EMPTY": ""})["EMPTY"] == ""


def test_neither_base_nor_extra_is_modified():
    base, extra = {"KEEP": "yes"}, {"ADDED": "1"}
    environment(base, extra=extra)
    assert (base, extra) == ({"KEEP": "yes"}, {"ADDED": "1"})


@pytest.mark.parametrize("name", ["TERM", "COLUMNS", "LINES", "PYTHONUTF8", "PYTHONIOENCODING"])
def test_extra_cannot_set_what_termsnap_sets_for_the_terminal(name: str):
    with pytest.raises(ValueError, match=name):
        environment(extra={name: "x"})


@pytest.mark.parametrize("name", ["NO_COLOR", "FORCE_COLOR", "CLICOLOR_FORCE"])
def test_extra_cannot_decide_the_color(name: str):
    with pytest.raises(ValueError, match=name):
        environment(extra={name: "1"})


def test_the_error_names_every_managed_variable_at_once():
    with pytest.raises(ValueError, match="COLUMNS, TERM"):
        environment(extra={"TERM": "x", "COLUMNS": "1", "FINE": "1"})


@pytest.mark.parametrize("value", [1, None, b"x", ["x"]])
def test_extra_values_must_be_strings(value: object):
    with pytest.raises(TypeError, match="MY_VAR"):
        environment(extra={"MY_VAR": value})
