"""
Окружение процесса "как у терминала".
"""

from collections.abc import Mapping

from termsnap.defaults import DEFAULT_TERM

#: Переменные, по которым программы включают цвет без терминала (Node.js, Python, git, ls и многие другие).
_COLOR_ON = {"FORCE_COLOR": "1", "CLICOLOR_FORCE": "1"}

#: Переменная-соглашение https://no-color.org: любое непустое значение выключает цвет у программ, которые ее знают.
_COLOR_OFF = "NO_COLOR"


def terminal_environment(
    base: Mapping[str, str], *, color: bool, columns: int, rows: int, term: str = DEFAULT_TERM
) -> dict[str, str]:
    """
    Окружение "как у терминала": тип и размер терминала, UTF-8 для Python, цвет включен или выключен принудительно.
    Из ``base`` убираются ``NO_COLOR`` и прежние ``FORCE_COLOR``/``CLICOLOR_FORCE``, чтобы цвет зависел только от
    аргумента ``color``.
    """
    env = {key: value for key, value in base.items() if key not in {_COLOR_OFF, *_COLOR_ON}}
    env |= {"TERM": term, "COLUMNS": str(columns), "LINES": str(rows), "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    if color:
        env |= _COLOR_ON
    else:
        env[_COLOR_OFF] = "1"
    return env
