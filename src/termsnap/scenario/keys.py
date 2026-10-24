"""
Клавиши: какие байты терминал посылает программе при нажатии.
"""

from dataclasses import dataclass
from typing import ClassVar

ESC = "\x1b"

#: Начало управляющей последовательности (CSI): ``ESC [``. Так посылаются стрелки, Home/End, PageUp/PageDown и F5-F12.
CSI = ESC + "["

#: Начало одиночного сдвига (SS3): ``ESC O``. Так посылаются F1-F4.
SS3 = ESC + "O"

#: Код Ctrl+буква равен порядковому номеру буквы в алфавите: ``A`` -> 1, ``C`` -> 3. Код заглавной латинской буквы
#: больше этого номера на 64.
_CONTROL_OFFSET = 64

#: Номер первой клавиши F, которая посылается в виде CSI с тильдой.
_FIRST_TILDE_KEY = 5


@dataclass(frozen=True, slots=True)
class Keys:
    """
    Символы, которые уходят программе как есть, без Enter: часть строки, клавиша, управляющая последовательность.
    """

    text: str


#: Буквы в последовательностях F1-F4 (``ESC O P`` ... ``ESC O S``).
_SS3_LETTERS = "PQRS"

#: Числа в последовательностях F5-F12 (``ESC [ 15 ~`` ... ``ESC [ 24 ~``). Пропуски (16 и 22) достались от
#: терминалов DEC VT220, xterm их сохранил.
_TILDE_NUMBERS = (15, 17, 18, 19, 20, 21, 23, 24)


def _function_keys() -> dict[int, Keys]:
    """
    F1-F4 в виде SS3, F5-F12 в виде CSI с тильдой, как у xterm.
    """
    short = {number: Keys(SS3 + letter) for number, letter in enumerate(_SS3_LETTERS, start=1)}
    long = {number: Keys(f"{CSI}{code}~") for number, code in enumerate(_TILDE_NUMBERS, start=_FIRST_TILDE_KEY)}
    return short | long


class Key:
    """
    Названия клавиш и последовательности, которые терминал посылает программе при их нажатии.
    """

    ENTER: ClassVar[Keys] = Keys("\r")
    TAB: ClassVar[Keys] = Keys("\t")
    ESC: ClassVar[Keys] = Keys(ESC)
    BACKSPACE: ClassVar[Keys] = Keys("\x7f")
    UP: ClassVar[Keys] = Keys(CSI + "A")
    DOWN: ClassVar[Keys] = Keys(CSI + "B")
    RIGHT: ClassVar[Keys] = Keys(CSI + "C")
    LEFT: ClassVar[Keys] = Keys(CSI + "D")
    HOME: ClassVar[Keys] = Keys(CSI + "H")
    END: ClassVar[Keys] = Keys(CSI + "F")
    PAGE_UP: ClassVar[Keys] = Keys(CSI + "5~")
    PAGE_DOWN: ClassVar[Keys] = Keys(CSI + "6~")
    DELETE: ClassVar[Keys] = Keys(CSI + "3~")
    CTRL_C: ClassVar[Keys] = Keys("\x03")
    CTRL_D: ClassVar[Keys] = Keys("\x04")
    F: ClassVar[dict[int, Keys]] = _function_keys()

    @staticmethod
    def ctrl(letter: str) -> Keys:
        """
        Ctrl вместе с латинской буквой: ``Key.ctrl("l")`` - очистка экрана.
        """
        if len(letter) != 1 or not letter.isascii() or not letter.isalpha():
            raise ValueError(f"нужна одна латинская буква, а не {letter!r}")
        return Keys(chr(ord(letter.upper()) - _CONTROL_OFFSET))
