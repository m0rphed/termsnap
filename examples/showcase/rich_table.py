"""
Таблица со скругленной рамкой, цветными столбцами, эмодзи в ячейках, заголовком и подписью.
"""

from _console import make
from rich import box
from rich.table import Table

console = make()
table = Table(title="Результаты испытаний", caption="Данные условные", box=box.ROUNDED, show_lines=True)
table.add_column("№", justify="right", style="cyan", no_wrap=True)
table.add_column("Название", style="bold magenta")
table.add_column("Статус", justify="center")
table.add_column("Время, с", justify="right", style="green")
table.add_row("1", "Загрузка данных", "[green]OK[/green]", "0.42")
table.add_row("2", "Обучение модели", "[yellow]медленно[/yellow]", "12.80")
table.add_row("3", "Проверка 🚀", "[red]ошибка ✗[/red]", "[bold]3.05[/bold]")
table.add_row("4", "Отчёт ✅", "[green]готово[/green]", "0.07")
console.print(table)
