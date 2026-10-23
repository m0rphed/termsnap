# termsnap

Рабочее название. Запуск команд и разбор их вывода с ANSI-цветами в нейтральную модель: строки, фрагменты, стили.
Модель не привязана к способу показа (Word, SVG, PNG) и к способу запуска (каналы, псевдотерминал).

Готово:

- запуск через каналы (`PipeBackend`, только стандартная библиотека);
- запуск в псевдотерминале (`PtyBackend`, `termsnap[pty]`): ConPTY в Windows, `pty` в Linux и macOS, экран ведет `pyte`;
- разбор SGR (16, 256 и 24-битные цвета, жирный, курсив и другие), возврат каретки и стирание строки;
- темы для перевода цветов палитры в RGB;
- рисование в PNG (`termsnap[png]`, Pillow) шрифтами, установленными в системе.

```python
from termsnap import DARK, run

capture = run(["node", "app.js"])
for line in capture.lines:
    for span in line.spans:
        foreground, background = DARK.colors_of(span.style)
        print(span.text, foreground.hex, background.hex)
```

## Псевдотерминал

Некоторым программам нужен настоящий терминал: `rich` и IPython в Windows при выводе в канал печатают без стилей,
`top` и подобные рисуют экран абсолютными позициями курсора, а длинный вывод уходит за границу экрана.

```python
from termsnap import PtyBackend, run

capture = run(["python", "app.py"], backend=PtyBackend(), columns=100, rows=30)
```

Программа видит терминал заданного размера (`isatty()` истинно, `COLORTERM=truecolor`), стандартный вывод и вывод
ошибок общие. Вывод читается как поток терминала, экран эмулирует `pyte` (`termsnap.screen`): строки, ушедшие за
верхнюю границу, сохраняются, длинные строки переносятся по ширине терминала, как в настоящем. Ввода нет:
программы, которые ждут ответа пользователя, не запустить. Размер терминала остается в `Capture.columns` и
`Capture.rows`.

## PNG

```python
from pathlib import Path

from termsnap import LIGHT, run
from termsnap.png import render_png

capture = run(["node", "app.js"])
Path("out.png").write_bytes(render_png(capture.lines, theme=LIGHT, font_size=14))
```

Шрифты в пакет не вшиваются. Семейство ищется среди установленных (`termsnap.png.find_family`), по умолчанию
берется первое подходящее из `DEFAULT_FAMILIES`, в котором есть все символы текста (так отсеиваются шрифты без
кириллицы). Источники сведений о шрифтах:

| Платформа | Основной источник | Запасной |
|---|---|---|
| Windows | реестр (`HKLM` и `HKCU`, `...\CurrentVersion\Fonts`) | обход `%WINDIR%\Fonts` и пользовательского каталога |
| Linux и прочие Unix | fontconfig (`fc-list`) | обход каталогов `XDG_DATA_DIRS` и `~/.fonts` |
| macOS | обход `/System/Library/Fonts`, `/Library/Fonts`, `~/Library/Fonts` | - |

Имена семейства и начертания читаются из самих файлов. Нужного жирного начертания нет (например, у вариативных
шрифтов вроде Cascadia Mono) - жирность имитируется, отсутствующий курсив заменяется прямым начертанием. Свой шрифт
задается файлами: `termsnap.png.from_files("MyMono-Regular.ttf", bold="MyMono-Bold.ttf")`.

## Проверки

Из каталога `termsnap`:

```bash
uv run pytest
uv run ruff check
uv run basedpyright
```

Тесты рисования и поиска шрифтов пропускаются, если в системе нет подходящего моноширинного шрифта с кириллицей.
