"""
Снимок экрана программы, которая сама не завершается: ждем нужный текст на экране, снимаем и останавливаем программу.

    uv run python examples/03_snapshot_of_a_running_program.py [каталог для картинки]

Так снимаются top, htop и подобные программы. Нужен ``termsnap[pty]`` и ``termsnap[png]``.
"""

import sys
from pathlib import Path

from termsnap import PtyBackend, Snapshot, run
from termsnap.png import render_png

#: Программа перерисовывает экран с начала (``ESC [H``) пять раз в секунду и сама не заканчивается.
PROGRAM = r"""
import time

print("\x1b[2J", end="")
count = 0
while True:
    count += 1
    print(f"\x1b[H\x1b[1;7m счетчик {count:>3} \x1b[0m\n\x1b[32mработает\x1b[0m", end="", flush=True)
    time.sleep(0.2)
"""


def main(out: Path) -> None:
    capture = run(
        [sys.executable, "-c", PROGRAM],
        backend=PtyBackend(),
        rows=5,
        # снять экран, когда счетчик дойдет до пяти, и остановить программу; ``after`` дает ей время дорисовать кадр
        snapshot=Snapshot(when=r"счетчик\s+5\b", after=0.1),
    )
    print("остановлена нами:", capture.stopped)
    for line in capture.lines:
        print(line.text)
    path = out / "03_snapshot.png"
    path.write_bytes(render_png(capture.lines))
    print("картинка:", path)


if __name__ == "__main__":
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out"
    directory.mkdir(parents=True, exist_ok=True)
    main(directory)
