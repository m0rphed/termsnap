"""
Клавиши сценария: последовательности совпадают с теми, что посылает xterm.
"""

import pytest
from helpers import ESC

from termsnap import Key, Keys


@pytest.mark.parametrize(
    ("key", "sequence"),
    [
        (Key.ENTER, "\r"),
        (Key.TAB, "\t"),
        (Key.ESC, ESC),
        (Key.BACKSPACE, "\x7f"),  # то, что посылает клавиша Backspace в xterm, а не Ctrl+H
    ],
    ids=["enter", "tab", "esc", "backspace"],
)
def test_editing_keys_are_single_control_characters(key: Keys, sequence: str):
    assert key.text == sequence


def test_function_keys_follow_the_xterm_table():
    assert {number: keys.text for number, keys in Key.F.items()} == {
        1: f"{ESC}OP",
        2: f"{ESC}OQ",
        3: f"{ESC}OR",
        4: f"{ESC}OS",
        5: f"{ESC}[15~",
        6: f"{ESC}[17~",
        7: f"{ESC}[18~",
        8: f"{ESC}[19~",
        9: f"{ESC}[20~",
        10: f"{ESC}[21~",
        11: f"{ESC}[23~",
        12: f"{ESC}[24~",
    }


@pytest.mark.parametrize(
    ("key", "sequence"),
    [
        (Key.UP, f"{ESC}[A"),
        (Key.DOWN, f"{ESC}[B"),
        (Key.RIGHT, f"{ESC}[C"),
        (Key.LEFT, f"{ESC}[D"),
        (Key.HOME, f"{ESC}[H"),
        (Key.END, f"{ESC}[F"),
        (Key.PAGE_UP, f"{ESC}[5~"),
        (Key.PAGE_DOWN, f"{ESC}[6~"),
        (Key.DELETE, f"{ESC}[3~"),
    ],
    ids=["up", "down", "right", "left", "home", "end", "page up", "page down", "delete"],
)
def test_navigation_keys_are_csi_sequences(key: Keys, sequence: str):
    assert key.text == sequence


@pytest.mark.parametrize(
    ("letter", "code"), [("a", "\x01"), ("C", "\x03"), ("d", "\x04"), ("l", "\x0c"), ("z", "\x1a")]
)
def test_ctrl_letter_is_the_position_of_the_letter_in_the_alphabet(letter: str, code: str):
    assert Key.ctrl(letter) == Keys(code)


def test_named_ctrl_keys_are_the_same_as_ctrl_letters():
    assert (Key.ctrl("c"), Key.ctrl("d")) == (Key.CTRL_C, Key.CTRL_D)


@pytest.mark.parametrize("bad", ["", "ab", "1", "ж", " "])
def test_ctrl_wants_exactly_one_latin_letter(bad: str):
    with pytest.raises(ValueError, match="латинская буква"):
        Key.ctrl(bad)
