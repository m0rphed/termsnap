from _console import make
from rich.syntax import Syntax

CODE = '''\
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float

    def distance(self, other: "Point") -> float:
        """Расстояние до другой точки."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


print(Point(0, 0).distance(Point(3, 4)))  # 5.0
'''
console = make()
console.print(Syntax(CODE, "python", theme="monokai", line_numbers=True, word_wrap=False))
console.print(Syntax(CODE.splitlines()[0] + "\nx = [i for i in range(10)]", "python", theme="default"))
