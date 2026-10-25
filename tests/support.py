"""
Что делать, когда для теста чего-то не хватает: модуля, шрифта, программы.

Два режима. Строгий (``TERMSNAP_STRICT=1``; его ставит ``ci/run.py test``, то есть CI и Docker) не знает слова
"пропустить": если нужного нет, тест падает с объяснением, потому что тихий пропуск делает прогон зеленым, ничего
не проверив.
Обычный (``uv run pytest`` на вашей машине) пропускает такой тест с причиной, чтобы можно было работать без части
зависимостей. Единственные ожидаемые пропуски - программы, которых на этой системе нет по определению
(``Program.absent`` в ``registry.py``); строгий режим принимает только их (см. ``conftest.py``).
"""

import importlib
import os
import sys
from types import ModuleType
from typing import NoReturn

import pytest

STRICT = os.environ.get("TERMSNAP_STRICT") == "1"

#: Начало причины ожидаемого пропуска: так ``conftest.py`` отличает его от остальных.
EXPECTED_SKIP = "ожидаемый пропуск"

#: Символы, которые должен покрывать основной шрифт, чтобы тесты русского вывода не рисовали пустые клетки.
FONT_COVERS = "АЯабвёЖ"


def missing(what: str, how_to_fix: str) -> NoReturn:
    """
    Тесту не хватает ``what``: в строгом режиме это ошибка с подсказкой ``how_to_fix``, иначе пропуск с причиной.
    """
    if STRICT:
        pytest.fail(f"{what}. {how_to_fix}", pytrace=False)
    pytest.skip(f"{what} ({how_to_fix})", allow_module_level=True)


def skip_on(system: str, reason: str):
    """
    Тест не имеет смысла на этой системе (``sys.platform``): ожидаемый пропуск с причиной, которую
    строгий режим принимает.
    """
    return pytest.mark.skipif(sys.platform == system, reason=f"{EXPECTED_SKIP}: {reason}")


def require_module(name: str) -> ModuleType:
    """
    Подключает необязательную зависимость (Pillow, pyte, winpty) или сообщает, что ее нет.
    """
    try:
        return importlib.import_module(name)
    except ImportError:
        missing(f"не установлен модуль {name}", "uv sync, нужны extras png и pty")


def require_pty_extras() -> None:
    """
    Псевдотерминалу нужен pyte, а в Windows еще и pywinpty.
    """
    require_module("pyte")
    if sys.platform == "win32":
        require_module("winpty")


def find_system_fonts():
    """
    Моноширинный шрифт системы с кириллицей или сообщение, что его нет (на Linux его ставит ``ci/run.py system-deps``).
    """
    require_module("PIL")
    from termsnap.errors import FontNotFound
    from termsnap.png import fonts

    try:
        return fonts.resolve(covers=FONT_COVERS)
    except FontNotFound as error:
        missing(
            f"в системе нет подходящего моноширинного шрифта: {error.problems}", "Linux: python ci/run.py system-deps"
        )
