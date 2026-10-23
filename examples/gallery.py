"""
Галерея: запускает все программы из ``registry``, рисует их вывод в PNG (каталог ``examples/out``) и печатает сводку.

Запуск из каталога termsnap:

    uv run python examples/gallery.py [--pty] [имя ...]

С ``--pty`` все программы запускаются в псевдотерминале (``PtyBackend``, нужен ``termsnap[pty]``) и к ним
добавляются программы, которым нужен терминал; картинки получают суффикс ``-pty``.
"""

import sys
from pathlib import Path

from registry import PTY_REGISTRY, REGISTRY

from termsnap import DARK, PtyBackend, run
from termsnap.png import render_png

OUT = Path(__file__).resolve().parent / "out"


def main(names: list[str], *, pty: bool) -> None:
    OUT.mkdir(exist_ok=True)
    backend = PtyBackend() if pty else None
    suffix = "-pty" if pty else ""
    print(f"{'программа':18} {'код':>3} {'строк':>5} {'ширина':>6} {'ESC':>3} {'с':>6}  png")
    for program in [*REGISTRY, *PTY_REGISTRY] if pty else REGISTRY:
        if names and program.name not in names:
            continue
        if not program.available:
            print(f"{program.name:18} пропущена: нет {program.tool}")
            continue
        capture = run(program.argv, timeout=60, backend=backend)
        width = max((line.width for line in capture.lines), default=0)
        stray = capture.text.count("\x1b")
        path = OUT / f"{program.name}{suffix}.png"
        path.write_bytes(render_png(capture.lines, theme=DARK, font_size=14))
        count = len(capture.lines)
        numbers = f"{capture.returncode:>3} {count:>5} {width:>6} {stray:>3} {capture.duration:>6.2f}"
        print(f"{program.name:18} {numbers}  {path.name}")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    main([name for name in arguments if name != "--pty"], pty="--pty" in arguments)
