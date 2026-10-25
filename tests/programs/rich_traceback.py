from _console import make


def divide(a: int, b: int) -> float:
    return a / b


def compute(values: list[int]) -> list[float]:
    return [divide(10, v) for v in values]


console = make()
try:
    compute([1, 2, 0])
except ZeroDivisionError:
    console.print_exception(show_locals=False, width=100)
