"""
Общая настройка тестов: уровень теста задает каталог, в котором он лежит.

    tests/unit/         функции и механизмы без запуска программ: время и вывод задаются вручную
    tests/integration/  настоящие процессы, которые написаны в проекте (в канале и в псевдотерминале)
    tests/external/     чужие команды (top, htop, IPython, node, pytest, ruff, git) на близких к жизни сценариях

Каталог превращается в маркер (``-m unit``), поэтому уровень не нужно помнить и писать в каждом файле. Тест вне этих
каталогов - ошибка сбора, а не молчаливая "ничья": любой тест должен иметь уровень.
"""

from collections.abc import Callable

import pytest
from registry import ALL_PROGRAMS

from termsnap import Capture, run

LEVELS = ("unit", "integration", "external")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        level = item.path.parent.name
        if level not in LEVELS:
            raise pytest.UsageError(f"тест {item.nodeid} лежит вне каталогов уровней {LEVELS}")
        item.add_marker(getattr(pytest.mark, level))


@pytest.fixture(scope="session")
def captures() -> Callable[[str], Capture]:
    """
    Запуск программы реестра в канале по имени; каждая программа запускается один раз на весь прогон.
    """
    cache: dict[str, Capture] = {}

    def get(name: str) -> Capture:
        if name not in cache:
            program = next(p for p in ALL_PROGRAMS if p.name == name)
            if not program.available:
                pytest.skip(f"нет программы {program.tool}")
            cache[name] = run(program.argv, timeout=60)
        return cache[name]

    return get


@pytest.fixture(scope="session")
def bundled_fonts(tmp_path_factory: pytest.TempPathFactory):
    """
    Подставной шрифт для проверок рисования: тот, что Pillow носит в себе (одинаков на любой машине), записанный в файл.
    Латиница, цифры и знаки препинания; кириллицы и эмодзи в нем нет, поэтому тексты в таких тестах - ASCII.
    """
    pytest.importorskip("PIL")
    from PIL import ImageFont

    from termsnap.png.fonts import Face, FontSet

    path = tmp_path_factory.mktemp("bundled-font") / "bundled.ttf"
    path.write_bytes(ImageFont.load_default(10).font_bytes)
    return FontSet("Bundled", Face("Bundled", "Regular", path))
