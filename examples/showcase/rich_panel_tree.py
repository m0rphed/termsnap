"""
Дерево каталогов в панели с заголовком и подписью и малая панель по размеру текста: эмодзи в рамке и цветные имена.
"""

from _console import make
from rich.panel import Panel
from rich.tree import Tree

console = make()
tree = Tree("📁 [bold blue]проект[/bold blue]")
src = tree.add("📁 [bold]src[/bold]")
src.add("🐍 [green]main.py[/green]")
src.add("🐍 [green]utils.py[/green]")
docs = tree.add("📁 docs")
docs.add("📄 [dim]README.md[/dim]")
docs.add("🖼  [yellow]схема.png[/yellow]")
tree.add("[red]🔒 .env[/red]")
console.print(
    Panel(tree, title="[bold]Структура[/bold]", subtitle="3 каталога", border_style="bright_blue", padding=(1, 2))
)
console.print(Panel.fit("[bold white on red] ВНИМАНИЕ [/bold white on red] Проверьте настройки", border_style="red"))
