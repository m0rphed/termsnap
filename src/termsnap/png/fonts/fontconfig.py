"""
Шрифты Linux и прочих Unix: fontconfig (``fc-list``), он же определяет шрифты в большинстве окружений рабочего стола.
"""

import re
import shutil
import subprocess
from pathlib import Path

from termsnap.png.fonts.face import Face

#: Формат вывода ``fc-list``: файл, номер шрифта в файле, семейство, стиль - через табуляцию.
FC_FORMAT = "%{file}\t%{index}\t%{family}\t%{style}\n"

#: Сколько полей в строке этого формата.
_FC_FIELDS = 4

#: Сколько секунд ждать ``fc-list``: при пустом кэше fontconfig он может строить его долго, но не бесконечно.
FC_LIST_TIMEOUT = 15

#: Старшие 16 бит номера в ``fc-list`` заняты номером именованного экземпляра вариативного шрифта.
_VARIABLE_INSTANCE_SHIFT = 16


def escape_value(value: str) -> str:
    """
    Экранирует значение для шаблона fontconfig (``:family=...``): знаки ``\\ - : , =`` получают обратную косую.
    """
    return re.sub(r"([\\\-:,=])", r"\\\1", value)


def parse_fc_list(output: str, family: str) -> list[Face]:
    """
    Начертания семейства из вывода ``fc-list --format "%{file}\\t%{index}\\t%{family}\\t%{style}\\n"``. В ответе
    fontconfig у семейства и стиля может быть несколько названий через запятую (на разных языках); берется первый
    стиль. Именованные экземпляры вариативных шрифтов (в индексе заняты старшие 16 бит) пропускаются: Pillow
    загружает такой файл с настройками по умолчанию, а не нужным экземпляром.
    """
    wanted = family.casefold()
    faces = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) != _FC_FIELDS:
            continue
        file, index, families, styles = parts
        if wanted not in {name.strip().casefold() for name in families.split(",")}:
            continue
        number = int(index) if index.isdigit() else 0
        if number >> _VARIABLE_INSTANCE_SHIFT:
            continue
        faces.append(Face(family, styles.split(",")[0].strip() or "Regular", Path(file), number))
    return faces


def fontconfig_faces(family: str) -> list[Face]:
    """
    Начертания семейства, найденные через ``fc-list``; пусто, если fontconfig не установлен или не ответил.
    """
    executable = shutil.which("fc-list")
    if executable is None:
        return []
    try:
        done = subprocess.run(
            [executable, "--format", FC_FORMAT, f":family={escape_value(family)}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=FC_LIST_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return parse_fc_list(done.stdout, family)
