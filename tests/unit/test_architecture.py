"""
Слои пакета: нижние слои не знают о верхних, необязательные зависимости не просачиваются в ядро.

Таблица ``ALLOWED`` - это и есть описание архитектуры: для каждого модуля верхнего уровня перечислено, что он вправе
импортировать. Новая зависимость вверх по слоям должна быть осознанным решением: сначала правится таблица (и ее
комментарии), потом код.
"""

import ast
from pathlib import Path

import termsnap

SOURCE = Path(termsnap.__file__).parent

#: Что вправе импортировать модуль или пакет верхнего уровня (внутри ``termsnap``). Снизу вверх:
ALLOWED: dict[str, set[str]] = {
    # основа: ни от чего не зависит
    "defaults": set(),
    "errors": set(),
    "extras": {"errors"},  # понятная ошибка, когда нет необязательной зависимости
    "width": set(),  # ширина символов в клетках терминала
    "scenario": set(),  # клавиши, паузы, момент снимка
    # модель вывода и то, что строится на ней
    "model": {"width"},
    "ansi": {"model", "width"},  # построчный разбор потока
    "theme": {"model"},  # цвета палитры
    "screen": {"ansi", "extras", "model", "width"},  # эмулятор экрана (нужен pyte)
    # запуск
    "request": {"defaults", "scenario"},
    "capture": {"defaults", "model"},
    "environment": {"defaults"},
    "backends": {"ansi", "errors", "extras", "model", "request", "scenario", "screen"},
    "runner": {"backends", "capture", "defaults", "environment", "request", "scenario"},
    # рисование в PNG (нужен Pillow): не знает ни о запуске, ни о разборе потока
    "png": {"errors", "extras", "model", "theme", "width"},
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


def layer_violations(allowed: dict[str, set[str]] = ALLOWED) -> list[str]:
    """
    Модули, которые импортируют слой, не разрешенный таблицей ``allowed`` (по умолчанию ``ALLOWED``).
    """
    found = []
    for path in modules():
        owner = top_level(path)
        if owner == "__init__":  # корень пакета собирает публичный интерфейс из всех слоев
            continue
        # "from termsnap.model import X" дает и "termsnap.model", и "termsnap.model.X": берется первый уровень
        used = {
            name.split(".")[1] if name.count(".") else "<root>"
            for name in imported(path)
            if name == "termsnap" or name.startswith("termsnap.")
        }
        extra = used - {owner} - allowed[owner]
        if extra:
            where = path.relative_to(SOURCE).as_posix()
            found.append(f"{where}: импортирует {sorted(extra)}, а слой {owner} вправе только {sorted(allowed[owner])}")
    return found


def optional_dependency_violations() -> list[str]:
    """
    Модули, которые импортируют необязательную зависимость вне ее пакета.
    """
    found = []
    for path in modules():
        relative = path.relative_to(SOURCE).parts
        for name in imported(path):
            home = OPTIONAL_DEPENDENCIES.get(name.split(".")[0])
            if home is not None and relative[: len(home)] != home:
                found.append(f"{'/'.join(relative)}: импортирует {name}, а ему можно только в {'/'.join(home)}")
    return found


def test_every_module_imports_only_what_its_layer_allows():
    assert layer_violations() == []


def test_every_top_level_module_is_described():
    assert {top_level(path) for path in modules()} - {"__init__"} == set(ALLOWED)


def test_optional_dependencies_stay_in_their_packages():
    assert optional_dependency_violations() == []


def test_the_layer_rule_notices_a_forbidden_import():
    # правило, которое ничего не находит, неотличимо от сломанного: слою png запрещаем все, и оно должно сработать
    violations = layer_violations({**ALLOWED, "png": set()})
    assert violations
    assert all(line.startswith("png/") for line in violations)
