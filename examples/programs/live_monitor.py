"""
Маленький «htop» для проверок снимка экрана: перерисовывает экран пять раз в секунду и сам не завершается.

Клавиши: ``q`` - выход, ``s`` - смена сортировки, стрелки вверх и вниз - выбор строки.
Данные выдуманы, чтобы экран можно было проверять точно, меняется только счетчик ``tick``.
"""

import sys
import time

ROWS = [
    ("postgres", 12.5, 8.1),
    ("python", 48.2, 3.4),
    ("node", 31.0, 6.7),
    ("nginx", 1.2, 0.9),
    ("redis", 0.8, 1.5),
    ("ffmpeg", 77.9, 2.2),
]
FRAME = 0.2


def frame(tick: int, by_cpu: bool, selected: int) -> str:
    rows = sorted(ROWS, key=(lambda row: -row[1]) if by_cpu else (lambda row: row[0]))
    out = ["\x1b[H", f"\x1b[1;7m monitor  tick {tick:>4}  sort: {'cpu' if by_cpu else 'name':<4} \x1b[0m\x1b[K\r\n\x1b[K\r\n"]
    out.append("\x1b[1m  NAME        CPU%   MEM%\x1b[0m\x1b[K\r\n")
    for index, (name, cpu, mem) in enumerate(rows):
        color = "\x1b[31m" if cpu > 40 else "\x1b[33m" if cpu > 10 else "\x1b[32m"
        line = f"{'>' if index == selected else ' '} {name:<10} {color}{cpu:>5.1f}\x1b[39m  {mem:>5.1f}"
        out.append(f"\x1b[7m{line}\x1b[27m\x1b[K\r\n" if index == selected else f"{line}\x1b[K\r\n")
    out.append("\x1b[K\r\n\x1b[2mq quit   s sort   up/down select\x1b[0m\x1b[K")
    return "".join(out)


def apply(key: str, by_cpu: bool, selected: int) -> tuple[bool, int, bool]:
    """
    Новое состояние после клавиши: сортировка, выбранная строка, нужно ли выйти.
    """
    if key == "q":
        return by_cpu, selected, True
    if key == "s":
        return not by_cpu, selected, False
    if key == "up":
        return by_cpu, max(selected - 1, 0), False
    if key == "down":
        return by_cpu, min(selected + 1, len(ROWS) - 1), False
    return by_cpu, selected, False


if sys.platform == "win32":
    import msvcrt

    def read_keys(timeout: float) -> list[str]:
        time.sleep(timeout)
        keys: list[str] = []
        while msvcrt.kbhit():
            char = msvcrt.getwch()
            if char in "\x00\xe0":
                keys.append({"H": "up", "P": "down"}.get(msvcrt.getwch(), ""))
            else:
                keys.append(char)
        return keys

    def setup() -> None:
        pass

    def restore() -> None:
        pass

else:
    import os
    import select
    import termios
    import tty

    _saved = termios.tcgetattr(sys.stdin.fileno())

    def read_keys(timeout: float) -> list[str]:
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if not ready:
            return []
        data = os.read(sys.stdin.fileno(), 64).decode(errors="replace")
        keys: list[str] = []
        while data:
            if data.startswith("\x1b[A"):
                keys.append("up")
                data = data[3:]
            elif data.startswith("\x1b[B"):
                keys.append("down")
                data = data[3:]
            else:
                keys.append(data[0])
                data = data[1:]
        return keys

    def setup() -> None:
        tty.setcbreak(sys.stdin.fileno())

    def restore() -> None:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, _saved)


def main() -> None:
    by_cpu, selected, tick, done = True, 0, 0, False
    setup()
    sys.stdout.write("\x1b[2J\x1b[?25l")
    try:
        while not done:
            sys.stdout.write(frame(tick, by_cpu, selected))
            sys.stdout.flush()
            tick += 1
            for key in read_keys(FRAME):
                by_cpu, selected, quit_now = apply(key, by_cpu, selected)
                done = done or quit_now
    finally:
        restore()
        sys.stdout.write("\x1b[?25h\r\n")


main()
