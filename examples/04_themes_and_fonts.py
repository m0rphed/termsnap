"""
Один и тот же вывод в разном оформлении: готовые темы, своя тема, шрифт, поля и масштаб.

    uv run python examples/04_themes_and_fonts.py [каталог для картинок]

Нужен ``termsnap[png]`` и установленный в системе моноширинный шрифт с кириллицей.
"""

import sys
from pathlib import Path

from termsnap import DARK, run
from termsnap.png import DEFAULT_FAMILIES, render_png

CODE = (
    "print('\x1b[1mверсии\x1b[0m')\n"
    "print('  \x1b[32mpython\x1b[0m 3.14   \x1b[33mrich\x1b[0m 15.0   \x1b[31mnode\x1b[0m нет')"
)


def main(out: Path) -> None:
    capture = run([sys.executable, "-c", CODE])

    # готовые темы выбираются по имени
    for name in ("dark", "light"):
        (out / f"04_{name}.png").write_bytes(render_png(capture.lines, theme=name))

    # своя тема: взять готовую и заменить отдельные цвета (по номеру 0-15 или по названию)
    solarized = DARK.derive(background="#002b36", foreground="#93a1a1", ansi={"green": "#859900", "red": "#dc322f"})
    (out / "04_custom_theme.png").write_bytes(render_png(capture.lines, theme=solarized))

    # шрифт: список семейств по предпочтению; в конце стандартные, чтобы не остаться без шрифта
    # (символы, которых нет в выбранном шрифте, рисуются запасными автоматически)
    families = ["JetBrains Mono", "Fira Code", *DEFAULT_FAMILIES]
    # поля вокруг текста (в пикселях "как на экране") и масштаб: 3 - картинка втрое подробнее для печати
    (out / "04_font_padding_scale.png").write_bytes(render_png(capture.lines, fonts=families, padding=24, scale=3))

    for path in sorted(out.glob("04_*.png")):
        print("картинка:", path)


if __name__ == "__main__":
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "out"
    directory.mkdir(parents=True, exist_ok=True)
    main(directory)
