"""
Клавиши сценария: последовательности совпадают с теми, что посылает xterm.
"""

import pytest

from termsnap import Key, Keys

ESC = "\x1b"


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


def test_cursor_keys_use_csi_and_home_end_are_not_confused():
    assert (Key.UP.text, Key.DOWN.text, Key.RIGHT.text, Key.LEFT.text) == (
        f"{ESC}[A",
        f"{ESC}[B",
        f"{ESC}[C",
        f"{ESC}[D",
    )
    assert (Key.HOME.text, Key.END.text) == (f"{ESC}[H", f"{ESC}[F")
    assert (Key.PAGE_UP.text, Key.PAGE_DOWN.text, Key.DELETE.text) == (f"{ESC}[5~", f"{ESC}[6~", f"{ESC}[3~")


def test_ctrl_letter_is_the_position_of_the_letter_in_the_alphabet():
    assert Key.ctrl("a") == Keys("\x01")
    assert Key.ctrl("C") == Key.CTRL_C == Keys("\x03")
    assert Key.ctrl("d") == Key.CTRL_D
    assert Key.ctrl("z") == Keys("\x1a")


@pytest.mark.parametrize("bad", ["", "ab", "1", "ж", " "])
def test_ctrl_wants_exactly_one_latin_letter(bad: str):
    with pytest.raises(ValueError, match="латинская буква"):
        Key.ctrl(bad)
