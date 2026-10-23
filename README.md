# termsnap

Рабочее название. Запуск команд и разбор их вывода с ANSI-цветами в нейтральную модель: строки, фрагменты, стили.
Модель не привязана к способу показа (Word, SVG, PNG) и к способу запуска (каналы, псевдотерминал).

Сейчас готово: запуск через каналы (`PipeBackend`, только стандартная библиотека), разбор SGR (16, 256 и 24-битные
цвета, жирный, курсив и другие), возврат каретки и стирание строки, темы для перевода цветов палитры в RGB.

```python
from termsnap import DARK, run

capture = run(["node", "app.js"])
for line in capture.lines:
    for span in line.spans:
        foreground, background = DARK.colors_of(span.style)
        print(span.text, foreground.hex, background.hex)
```

Проверки (из каталога `termsnap`):

```bash
uv run pytest
uv run ruff check
uv run basedpyright
```
