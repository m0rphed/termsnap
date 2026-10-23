import time

from _console import make
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeElapsedColumn

console = make()
with Progress(
    TextColumn("[bold blue]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    TimeElapsedColumn(),
    console=console,
) as progress:
    first = progress.add_task("Скачивание", total=40)
    second = progress.add_task("Обработка", total=40)
    for _ in range(40):
        progress.update(first, advance=1)
        progress.update(second, advance=0.5)
        time.sleep(0.01)
    progress.update(second, completed=40)
console.print("[green]Готово[/green]")
