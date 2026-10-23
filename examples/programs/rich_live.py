import time

from _console import make
from rich.live import Live
from rich.table import Table


def frame(step: int) -> Table:
    table = Table(title=f"Шаг {step}")
    table.add_column("Узел")
    table.add_column("Нагрузка", justify="right")
    for node in range(3):
        table.add_row(f"node-{node}", f"{(step * 7 + node * 13) % 100}%")
    return table


console = make()
with Live(frame(0), console=console, refresh_per_second=50) as live:
    for step in range(1, 6):
        time.sleep(0.05)
        live.update(frame(step))
console.print("[bold]Итог: пять обновлений[/bold]")
