"""
Самое простое: запустить команду, получить ее вывод со стилями и сохранить скриншот.

    uv run python examples/01_capture_a_command.py [каталог для картинки]

Нужен ``termsnap[png]`` (Pillow) и установленный в системе моноширинный шрифт с кириллицей.
"""

import sys
from pathlib import Path

from termsnap import run
from termsnap.png import render_png

#: Команда печатает две строки с цветом: зеленая "ok" и красная "fail" (коды ANSI в строках Python).
CODE = "print('\x1b[1;32mok\x1b[0m: проверка прошла'); print('\x1b[31mfail\x1b[0m: проверка не прошла')"


def main(out: Path) -> None:
    capture = run([sys.executable, "-c", CODE])
    print(f"код возврата {capture.returncode}, строк {len(capture.lines)}, времени {capture.duration:.2f} с")
    for line in capture.lines:
        print(repr(line.text))
        for span in line.spans:  # фрагмент - текст с одним стилем
            print(f"    {span.text!r:28} цвет {span.style.fg}, жирный {span.style.bold}")
    path = out / "01_capture.png"
    path.write_bytes(render_png(capture.lines))
    print("картинка:", path)


if __name__ == "__main__":
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out"
    directory.mkdir(parents=True, exist_ok=True)
    main(directory)
