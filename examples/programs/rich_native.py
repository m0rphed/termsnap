"""
Самый обычный rich без каких-либо настроек консоли: цвет, ширину и режим rich определяет сам по терминалу. В канале на
Windows так получается вывод без стилей, в псевдотерминале - полный.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
print(f"терминал: {console.is_terminal}, цвета: {console.color_system}, ширина: {console.width}")

table = Table(title="Результаты", border_style="cyan")
table.add_column("Тест", style="bold")
table.add_column("Статус", justify="center")
table.add_column("Время, с", justify="right", style="dim")
table.add_row("парсер", "[green]✅ ok[/green]", "0.12")
table.add_row("рендер", "[red]❌ fail[/red]", "1.40")
table.add_row("шрифты", "[yellow]⚠️ warn[/yellow]", "0.07")
console.print(table)
console.print(Panel("[bold red]ВНИМАНИЕ[/] Проверьте настройки", border_style="red"))
