"""
Псевдотерминал сообщает программам о 24-битном цвете, если пользователь не задал свое значение.
"""

from termsnap import Request
from termsnap.backends.pty.backend import _with_truecolor


def request(**env: str) -> Request:
    return Request(argv=("x",), env=env, rows=7)


def test_truecolor_is_announced_when_the_environment_does_not_say_anything():
    assert _with_truecolor(request(PATH="/bin")).env == {"PATH": "/bin", "COLORTERM": "truecolor"}


def test_a_value_chosen_by_the_user_is_kept():
    ready = request(COLORTERM="24bit")
    assert _with_truecolor(ready) is ready


def test_an_empty_value_is_also_a_choice_of_the_user():
    assert _with_truecolor(request(COLORTERM="")).env == {"COLORTERM": ""}


def test_the_rest_of_the_request_and_the_original_environment_stay_the_same():
    original = request(PATH="/bin")
    changed = _with_truecolor(original)
    assert (changed.argv, changed.rows) == (original.argv, original.rows)
    assert original.env == {"PATH": "/bin"}
