"""
Разное: градиент в 24-битных цветах, все атрибуты текста, гиперссылка, колонки, эмодзи, иероглифы и рамки из символов.
"""

from _console import make
from rich.columns import Columns
from rich.rule import Rule
from rich.text import Text

console = make(color_system="truecolor")
console.print(Rule("[bold]Градиент и стили[/bold]"))
gradient = Text()
for index in range(60):
    gradient.append("█", style=f"rgb({255 - index * 4},{index * 4},128)")
console.print(gradient)
console.print(
    "[bold]жирный[/] [italic]курсив[/] [underline]подчёркнутый[/] "
    "[strike]зачёркнутый[/] [dim]тусклый[/] [reverse]обратный[/]"
)
console.print("[link=https://example.com]ссылка с гиперссылкой OSC 8[/link] и [on blue] фон [/on blue]")
console.print(Rule(style="dim"))
console.print(
    Columns(
        [f"[cyan]{name}[/cyan]" for name in ("альфа", "бета", "гамма", "дельта", "эпсилон", "дзета")],
        equal=True,
        expand=True,
    )
)
console.print("Эмодзи: 🚀 ✅ ❌ ⚠️ 🐍  Иероглифы: 日本語 中文  Рамки: ┌─┬─┐│ │ │└─┴─┘")
