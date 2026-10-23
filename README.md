# termsnap

Рабочее название. Запуск команд и разбор их вывода с ANSI-цветами в нейтральную модель: строки, фрагменты, стили.
Модель не привязана к способу показа (Word, SVG, PNG) и к способу запуска (каналы, псевдотерминал).

Готово:

- запуск через каналы (`PipeBackend`, только стандартная библиотека);
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
