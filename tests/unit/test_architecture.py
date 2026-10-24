"""
Слои пакета: нижние слои не знают о верхних, необязательные зависимости не просачиваются в ядро.

Таблица ``ALLOWED`` - это и есть описание архитектуры: для каждого модуля верхнего уровня перечислено, что он вправе
импортировать. Новая зависимость вверх по слоям должна быть осознанным решением: сначала правится таблица (и ее
комментарии), потом код.
"""

import ast
from pathlib import Path

import pytest

import termsnap

SOURCE = Path(termsnap.__file__).parent

#: Что вправе импортировать модуль или пакет верхнего уровня (внутри ``termsnap``). Снизу вверх:
ALLOWED: dict[str, set[str]] = {
    # основа: ни от чего не зависит
    "defaults": set(),
    "errors": set(),
    "width": set(),  # ширина символов в клетках терминала
    "scenario": set(),  # клавиши, паузы, момент снимка
    # модель вывода и то, что строится на ней
    "model": {"width"},
    "ansi": {"model", "width"},  # построчный разбор потока
    "theme": {"model"},  # цвета палитры
    "screen": {"ansi", "model", "width"},  # эмулятор экрана (нужен pyte)
    # запуск
    "request": {"defaults", "scenario"},
    "capture": {"defaults", "model"},
    "environment": {"defaults"},
    "backends": {"ansi", "errors", "model", "request", "scenario", "screen"},
    "runner": {"backends", "capture", "defaults", "environment", "request", "scenario"},
    # рисование в PNG (нужен Pillow): не знает ни о запуске, ни о разборе потока
    "png": {"errors", "model", "theme", "width"},
}

#: Где разрешено импортировать необязательную зависимость (по частям пути относительно ``termsnap``).
OPTIONAL_DEPENDENCIES = {
    "PIL": ("png",),
    "pyte": ("screen",),
    "winpty": ("backends", "pty", "conpty.py"),
    "winreg": ("png", "fonts", "windows.py"),
}


def modules() -> list[Path]:
    return sorted(path for path in SOURCE.rglob("*.py") if "__pycache__" not in path.parts)


def imported(path: Path) -> set[str]:
    """
    Имена всех импортируемых модулей файла, в том числе внутри функций (отложенные импорты тоже зависимости).
    """
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


def top_level(path: Path) -> str:
    return path.relative_to(SOURCE).parts[0].removesuffix(".py")


@pytest.mark.parametrize("path", modules(), ids=lambda path: str(path.relative_to(SOURCE)))
def test_module_imports_only_what_its_layer_allows(path: Path):
    owner = top_level(path)
    if owner == "__init__":  # корень пакета собирает публичный интерфейс из всех слоев
        return
    used = {
        name.split(".")[1] if name.count(".") else "<root>"
        for name in imported(path)
        if name == "termsnap" or name.startswith("termsnap.")
    }
    used -= {owner}
    # "from termsnap.model import X" даст и "termsnap.model", и "termsnap.model.X": лишнее отбрасываем по первому уровню
    assert used <= ALLOWED[owner], (
        f"{owner} импортирует {sorted(used - ALLOWED[owner])}, а вправе только {sorted(ALLOWED[owner])}"
    )


def test_every_top_level_module_is_described():
    assert {top_level(path) for path in modules()} - {"__init__"} == set(ALLOWED)


@pytest.mark.parametrize("path", modules(), ids=lambda path: str(path.relative_to(SOURCE)))
def test_optional_dependencies_stay_in_their_packages(path: Path):
    relative = path.relative_to(SOURCE).parts
    for name in imported(path):
        home = OPTIONAL_DEPENDENCIES.get(name.split(".")[0])
        if home is not None:
            assert relative[: len(home)] == home, (
                f"{path.name} импортирует {name}, а ему можно только в {'/'.join(home)}"
            )
