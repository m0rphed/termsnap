"""
Сценарий для интерактивной программы: что напечатать, чего подождать и когда снимать экран.

    run(["htop"], backend=PtyBackend(), input=[Key.DOWN, Key.DOWN, Pause(1)], snapshot=Snapshot(after=2))

В ``input`` обычная строка печатается с Enter, ``Keys`` - как есть (без Enter), ``Key`` - готовые клавиши,
``Pause`` - просто ждет.
"""

from dataclasses import dataclass
from typing import ClassVar

_ESC = "\x1b"


@dataclass(frozen=True, slots=True)
class Keys:
    """
    Символы, которые уходят программе как есть, без Enter: часть строки, клавиша, управляющая последовательность.
    """

    text: str


@dataclass(frozen=True, slots=True)
class Pause:
    """
    Подождать ``seconds`` секунд, прежде чем двигаться дальше.
    """

    seconds: float


class Key:
    """
    Названия клавиш и последовательности, которые терминал посылает программе при их нажатии.
    """

    ENTER: ClassVar[Keys] = Keys("\r")
    TAB: ClassVar[Keys] = Keys("\t")
    ESC: ClassVar[Keys] = Keys(_ESC)
    BACKSPACE: ClassVar[Keys] = Keys("\x7f")
    UP: ClassVar[Keys] = Keys(f"{_ESC}[A")
    DOWN: ClassVar[Keys] = Keys(f"{_ESC}[B")
    RIGHT: ClassVar[Keys] = Keys(f"{_ESC}[C")
    LEFT: ClassVar[Keys] = Keys(f"{_ESC}[D")
    HOME: ClassVar[Keys] = Keys(f"{_ESC}[H")
    END: ClassVar[Keys] = Keys(f"{_ESC}[F")
    PAGE_UP: ClassVar[Keys] = Keys(f"{_ESC}[5~")
    PAGE_DOWN: ClassVar[Keys] = Keys(f"{_ESC}[6~")
    DELETE: ClassVar[Keys] = Keys(f"{_ESC}[3~")
    CTRL_C: ClassVar[Keys] = Keys("\x03")
    CTRL_D: ClassVar[Keys] = Keys("\x04")
    #: F1-F4 в виде SS3, F5-F12 в виде CSI, как у xterm.
    F: ClassVar[dict[int, Keys]] = {
        1: Keys(f"{_ESC}OP"),
        2: Keys(f"{_ESC}OQ"),
        3: Keys(f"{_ESC}OR"),
        4: Keys(f"{_ESC}OS"),
        5: Keys(f"{_ESC}[15~"),
        6: Keys(f"{_ESC}[17~"),
        7: Keys(f"{_ESC}[18~"),
        8: Keys(f"{_ESC}[19~"),
        9: Keys(f"{_ESC}[20~"),
        10: Keys(f"{_ESC}[21~"),
        11: Keys(f"{_ESC}[23~"),
        12: Keys(f"{_ESC}[24~"),
    }

    @staticmethod
    def ctrl(letter: str) -> Keys:
        """
        Ctrl вместе с латинской буквой: ``Key.ctrl("l")`` - очистка экрана.
        """
        if len(letter) != 1 or not letter.isascii() or not letter.isalpha():
            raise ValueError(f"нужна одна латинская буква, а не {letter!r}")
        return Keys(chr(ord(letter.upper()) - 64))


type Step = str | Keys | Pause


@dataclass(frozen=True, slots=True)
class Snapshot:
    """
    Когда снимать экран у программы, которая сама не завершается (``htop``, ``top``, ``nvtop``), и остановить ее.

    Экран снимается, когда выполнены все условия: ``input`` напечатан целиком, ``when`` (регулярное выражение)
    нашлось в тексте экрана, прошло ``after`` секунд с последнего из этих событий. Если указано только ``after``,
    отсчет идет от запуска (или от последней напечатанной строки). Не дождались - ``RunTimeout`` по общему
    времени ``timeout``.
    """

    after: float = 0.0
    when: str | None = None
