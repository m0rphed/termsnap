"""
Сообщает, что получило от терминала при каждом нажатии: имя клавиши и сами байты.

Терминал переводится в "сырой" режим: без эха, без построчного ввода и без обработки Ctrl+C сигналом, поэтому программа
видит ровно то, что послал ``PtyBackend``. Клавиша ``q`` завершает программу. Одна клавиша - одно чтение, поэтому
сценарий должен делать между клавишами паузу, пока программа не напечатает приглашение (так работает ``prompt``).
"""

import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager

NAMES = {
    b"\r": "enter",
    b"\t": "tab",
    b"\x1b": "esc",
    b"\x7f": "backspace",
    b"\x03": "ctrl+c",
    b"\x04": "ctrl+d",
    b"\x1b[A": "up",
    b"\x1b[B": "down",
    b"\x1b[C": "right",
    b"\x1b[D": "left",
    b"\x1b[H": "home",
    b"\x1b[F": "end",
    b"\x1b[3~": "delete",
    b"\x1b[5~": "page up",
    b"\x1b[6~": "page down",
    b"\x1bOP": "f1",
    b"\x1b[15~": "f5",
}

PROMPT = "> "


@contextmanager
def raw_terminal() -> Iterator[None]:
    """
    Сырой ввод: в Linux и macOS через ``termios``, в Windows режимом консоли с виртуальными последовательностями.
    """
    if sys.platform == "win32":
        import ctypes

        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-10)  # STD_INPUT_HANDLE
        saved = ctypes.c_uint()
        kernel.GetConsoleMode(handle, ctypes.byref(saved))
        processed, line, echo, virtual = 0x0001, 0x0002, 0x0004, 0x0200
        kernel.SetConsoleMode(handle, (saved.value & ~(processed | line | echo)) | virtual)
        try:
            yield
        finally:
            kernel.SetConsoleMode(handle, saved.value)
    else:
        import termios
        import tty

        saved_attributes = termios.tcgetattr(sys.stdin.fileno())
        tty.setraw(sys.stdin.fileno())
        try:
            yield
        finally:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, saved_attributes)


def describe(chunk: bytes) -> str:
    if chunk in NAMES:
        return NAMES[chunk]
    if len(chunk) == 1 and chunk.isascii() and chunk.isalnum():
        return f"letter {chunk.decode()}"
    return f"bytes {chunk!r}"


def main() -> None:
    with raw_terminal():
        sys.stdout.write("keys: press anything, q quits\r\n" + PROMPT)
        sys.stdout.flush()
        while chunk := os.read(sys.stdin.fileno(), 32):
            if chunk == b"q":
                sys.stdout.write("bye\r\n")
                break
            sys.stdout.write(f"{describe(chunk)}\r\n{PROMPT}")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
