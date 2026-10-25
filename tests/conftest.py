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
from registry import ALL_PROGRAMS, require
from support import EXPECTED_SKIP, STRICT, find_system_fonts, require_module, require_pty_extras

from termsnap import Capture, PtyBackend, run

LEVELS = ("unit", "integration", "external")

#: Программы, которые запускают тесты, - не тесты: pytest их не собирает (``failing_cases.py`` падает намеренно).
collect_ignore_glob = ["programs/*"]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        level = item.path.parent.name
        if level not in LEVELS:
            raise pytest.UsageError(f"тест {item.nodeid} лежит вне каталогов уровней {LEVELS}")
        item.add_marker(getattr(pytest.mark, level))


def pytest_sessionfinish(session: pytest.Session) -> None:
    """
    Строгий режим (CI): пропущен может быть только тест программы, которой на этой системе нет по определению
    (``Program.absent``; ``registry.require`` начинает причину с ``EXPECTED_SKIP``). Любой другой пропуск - ошибка.
    """
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    skipped = reporter.stats.get("skipped", []) if reporter else []
    unexpected = [report for report in skipped if not str(report.longrepr[2]).startswith(f"Skipped: {EXPECTED_SKIP}")]
    if STRICT and unexpected:
        print("неожиданные пропуски в строгом режиме (TERMSNAP_STRICT=1):")
        for report in unexpected:
            print(f"  {report.nodeid}: {report.longrepr[2]}")
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


@pytest.fixture(scope="session")
def system_fonts():
    """
    Моноширинный шрифт системы с кириллицей: нужен тестам, которые проверяют сам поиск шрифтов и полный путь от
    команды до картинки. Остальным тестам рисования хватает ``bundled_fonts``.
    """
    return find_system_fonts()


@pytest.fixture(scope="session")
def captures() -> Callable[[str], Capture]:
    """
    Запуск программы реестра в канале по имени; каждая программа запускается один раз на весь прогон.
    """
    cache: dict[str, Capture] = {}

    def get(name: str) -> Capture:
        if name not in cache:
            program = next(p for p in ALL_PROGRAMS if p.name == name)
            require(program)
            cache[name] = run(program.argv, timeout=60, **program.options)
        return cache[name]

    return get


@pytest.fixture(scope="session")
def pty_captures() -> Callable[[str], Capture]:
    """
    То же, что ``captures``, но в псевдотерминале: так запускаются программы с вводом и снимками экрана.
    """
    require_pty_extras()
    backend = PtyBackend()
    cache: dict[str, Capture] = {}

    def get(name: str) -> Capture:
        if name not in cache:
            program = next(p for p in ALL_PROGRAMS if p.name == name)
            require(program)
            cache[name] = run(program.argv, backend=backend, timeout=120, **program.options)
        return cache[name]

    return get


@pytest.fixture(scope="session")
def bundled_fonts(tmp_path_factory: pytest.TempPathFactory):
    """
    Подставной шрифт для проверок рисования: тот, что Pillow носит в себе (одинаков на любой машине), записанный в файл.
    Латиница, цифры и знаки препинания; кириллицы и эмодзи в нем нет, поэтому тексты в таких тестах - ASCII.
    """
    require_module("PIL")
    from PIL import ImageFont

    from termsnap.png.fonts import Face, FontSet

    path = tmp_path_factory.mktemp("bundled-font") / "bundled.ttf"
    path.write_bytes(ImageFont.load_default(10).font_bytes)
    return FontSet("Bundled", Face("Bundled", "Regular", path))
