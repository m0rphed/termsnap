from _console import make
from rich.markdown import Markdown

TEXT = """\
# Заголовок первого уровня

Обычный абзац с **жирным**, *курсивом*, `кодом` и [ссылкой](https://example.com).

## Список

- первый пункт
- второй пункт
  - вложенный пункт
1. нумерованный
2. список

> Цитата, которая занимает несколько слов.

```python
def hello(name: str) -> str:
    return f"Привет, {name}!"
```

---
"""
make(width=50).print(Markdown(TEXT))
