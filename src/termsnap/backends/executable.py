"""
Поиск запускаемого файла.
"""

import shutil

from termsnap.request import Request


def find_executable(request: Request) -> str:
    """
    Полный путь к программе ``request.argv[0]``. Ищется по ``PATH`` из окружения запроса (а не нашего процесса):
    программа должна найтись так же, как найдется при запуске; иначе ``FileNotFoundError``.
    """
    executable = shutil.which(request.argv[0], path=request.env.get("PATH"))
    if executable is None:
        raise FileNotFoundError(f"программа {request.argv[0]!r} не найдена в PATH")
    return executable
