"""
Галерея: запускает программы из ``showcase``, рисует их вывод в PNG и печатает сводку.

    uv run python examples/gallery.py [--pty] [--out КАТАЛОГ] [имя ...]

Без параметров картинки лежат в ``examples/out``, программы запускаются в канале (так их вывод получается у любой
программы). С ``--pty`` запуск идет в псевдотерминале (``PtyBackend``, нужен ``termsnap[pty]``): программа видит
настоящий терминал, а к имени картинки добавляется ``-pty``. Нужен ``termsnap[png]``.
"""

import argparse
import sys
from pathlib import Path

from termsnap import DARK, PtyBackend, run
from termsnap.png import render_png

HERE = Path(__file__).resolve().parent
SHOWCASE = HERE / "showcase"


def programs() -> list[Path]:
    """
    Программы витрины: все скрипты каталога, кроме вспомогательных (имена на подчеркивание).
    """
    return sorted(path for path in SHOWCASE.glob("*.py") if not path.name.startswith("_"))


def main(names: list[str], *, pty: bool, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    backend = PtyBackend() if pty else None
    suffix = "-pty" if pty else ""
    print(f"{'программа':18} {'код':>3} {'строк':>5} {'ширина':>6} {'с':>6}  картинка")
    for script in programs():
        if names and script.stem not in names:
            continue
        capture = run([sys.executable, str(script)], backend=backend, timeout=120)
        width = max((line.width for line in capture.lines), default=0)
        path = out / f"{script.stem}{suffix}.png"
        path.write_bytes(render_png(capture.lines, theme=DARK, font_size=14))
        numbers = f"{capture.returncode:>3} {len(capture.lines):>5} {width:>6} {capture.duration:>6.2f}"
        print(f"{script.stem:18} {numbers}  {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1] if __doc__ else None)
    parser.add_argument("names", nargs="*", help="какие программы запустить (по умолчанию все)")
    parser.add_argument("--pty", action="store_true", help="запускать в псевдотерминале")
    parser.add_argument("--out", type=Path, default=HERE / "out", help="каталог для картинок")
    arguments = parser.parse_args()
    main(arguments.names, pty=arguments.pty, out=arguments.out)
