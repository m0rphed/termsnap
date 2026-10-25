"""
Проверка необязательных зависимостей: понятная ошибка вместо ``ModuleNotFoundError`` из глубины пакета.
"""

import importlib

from termsnap.errors import MissingExtra


def need(module: str, extra: str, purpose: str) -> None:
    """
    Убеждается, что ``module`` импортируется; иначе ``MissingExtra`` с подсказкой ``pip install termsnap[extra]``.
    Вызывается в начале пакета (или действия), которому модуль нужен, чтобы ошибка появилась до долгой работы:
    например, до запуска программы в псевдотерминале, вывод которой потом нечем разобрать.
    """
    try:
        importlib.import_module(module)
    except ImportError as error:
        raise MissingExtra(module, extra, purpose) from error
