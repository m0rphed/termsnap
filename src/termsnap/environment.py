"""
Окружение процесса "как у терминала".
"""

from collections.abc import Mapping

from termsnap.defaults import DEFAULT_TERM

#: Переменные, по которым программы включают цвет без терминала (Node.js, Python, git, ls и многие другие).
_COLOR_ON = {"FORCE_COLOR": "1", "CLICOLOR_FORCE": "1"}

#: Переменная-соглашение https://no-color.org: любое непустое значение выключает цвет у программ, которые ее знают.
_COLOR_OFF = "NO_COLOR"

#: Python программы пишет в UTF-8 независимо от кодировки консоли, чтобы вывод разбирался однозначно.
_PYTHON_UTF8 = {"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}

#: Имена, значения которых задает сам termsnap (тип и размер терминала, цвет, кодировка Python): ``extra`` их
#: переопределить не может, чтобы заданное явно не пропадало молча.
_MANAGED = frozenset({"TERM", "COLUMNS", "LINES", *_PYTHON_UTF8, _COLOR_OFF, *_COLOR_ON})


def terminal_environment(
    base: Mapping[str, str],
    *,
    color: bool,
    columns: int,
    rows: int,
    term: str = DEFAULT_TERM,
    extra: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """
    Окружение, которое увидит процесс. Собирается слоями, каждый следующий перекрывает предыдущие:

    1. ``base`` - исходное окружение целиком (без ``NO_COLOR``, ``FORCE_COLOR`` и ``CLICOLOR_FORCE``: цвет зависит
       только от аргумента ``color``);
    2. ``extra`` - переменные, которые нужно добавить или заменить; остальные из ``base`` остаются. Значения должны
       быть строками, а имена - не из числа тех, что задает termsnap (``ValueError``);
    3. переменные терминала: тип (``TERM``) и размер (``COLUMNS``, ``LINES``), UTF-8 для Python и цвет - включен
       (``FORCE_COLOR``, ``CLICOLOR_FORCE``) или выключен (``NO_COLOR``) принудительно.

    ``base`` и ``extra`` не изменяются.
    """
    if extra:
        _check_extra(extra)
    env = {key: value for key, value in base.items() if key not in {_COLOR_OFF, *_COLOR_ON}}
    env |= extra or {}
    env |= {"TERM": term, "COLUMNS": str(columns), "LINES": str(rows), **_PYTHON_UTF8}
    if color:
        env |= _COLOR_ON
    else:
        env[_COLOR_OFF] = "1"
    return env


def _check_extra(extra: Mapping[str, str]) -> None:
    managed = sorted(_MANAGED & extra.keys())
    if managed:
        raise ValueError(
            f"extra_env задает переменные, которые назначает сам termsnap: {', '.join(managed)} "
            "(размер терминала и цвет меняются аргументами columns, rows и color)"
        )
    for name, value in extra.items():
        if not isinstance(value, str):
            raise TypeError(f"значение переменной {name} в extra_env должно быть строкой, получено {value!r}")
