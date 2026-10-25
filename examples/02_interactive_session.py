"""
Сеанс с интерактивной программой: ввод печатается по сценарию, на экране остаются и приглашения, и ответы.

    uv run python examples/02_interactive_session.py [каталог для картинки]

Нужен ``termsnap[pty]`` и ``termsnap[png]``. Программе нужен терминал, поэтому запуск идет через ``PtyBackend``.
"""

import os
import sys
from pathlib import Path

from termsnap import PtyBackend, run
from termsnap.png import render_png

#: Ввод по шагам: каждая строка набирается, когда программа снова показала приглашение.
INPUT = ("6 * 7", "import math", "math.pi", "exit()")

#: Приглашение Python (три знака ``>`` и пробел). Пробел в конце строки экрана отбрасывается, поэтому в шаблоне его нет.
PROMPT = r">>>$"


def main(out: Path) -> None:
    capture = run(
        [sys.executable, "-q"],
        backend=PtyBackend(),
        # обычная оболочка Python: у нового интерактивного режима (3.13+) своя раскраска и свои запросы к терминалу
        env={**os.environ, "PYTHON_BASIC_REPL": "1"},
        input=INPUT,
        prompt=PROMPT,
    )
    for line in capture.lines:
        print(line.text)
    path = out / "02_session.png"
    path.write_bytes(render_png(capture.lines))
    print("картинка:", path)


if __name__ == "__main__":
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out"
    directory.mkdir(parents=True, exist_ok=True)
    main(directory)
