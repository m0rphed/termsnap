"""
Ядро пакета без необязательных зависимостей: оно работает и не тянет их, а то, что их требует, сообщает об этом понятно.

Отсутствие Pillow, pyte и pywinpty изображается в чистом интерпретаторе: в ``sys.modules`` вместо модуля кладется
``None``, и ``import`` падает так же, как если бы пакета не было.
"""

import subprocess
import sys
from pathlib import Path

from support import skip_on

OPTIONAL = ("PIL", "pyte", "winpty")


def interpreter(code: str, *arguments: str, absent: tuple[str, ...] = OPTIONAL) -> subprocess.CompletedProcess[str]:
    """
    Выполняет ``code`` в изолированном интерпретаторе (без пользовательских пакетов), где нет модулей ``absent``.
    """
    hide = f"import sys\nfor name in {absent!r}:\n    sys.modules[name] = None\n"
    # -X utf8: -I не читает PYTHONUTF8, а ошибки по-русски, и без этого Windows пишет их в кодовой странице консоли
    return subprocess.run(
        [sys.executable, "-I", "-X", "utf8", "-c", hide + code, *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_core_import_does_not_pull_optional_dependencies():
    code = (
        "import sys, termsnap, termsnap.backends\n"
        "loaded = {name for name in ('PIL', 'pyte', 'winpty') if name in sys.modules}\n"
        "assert not loaded, loaded\n"
    )
    done = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr


def test_a_pipe_run_works_without_any_optional_dependency():
    code = (
        "from termsnap import run\n"
        "import sys\n"
        "capture = run([sys.executable, '-c', 'print(1)'])\n"
        "assert capture.text == '1', capture.text\n"
    )
    done = interpreter(code)
    assert done.returncode == 0, done.stderr


def test_drawing_without_pillow_says_which_extra_to_install():
    done = interpreter("import termsnap.png\n")
    assert done.returncode != 0
    assert "MissingExtra" in done.stderr
    assert "pip install termsnap[png]" in done.stderr


def test_the_terminal_emulator_without_pyte_says_which_extra_to_install():
    done = interpreter("import termsnap.screen\n")
    assert done.returncode != 0
    assert "pip install termsnap[pty]" in done.stderr


PTY_RUN = (
    "import sys\n"
    "from termsnap import PtyBackend, run\n"
    "from termsnap.errors import MissingExtra\n"
    "touch = 'import pathlib, sys; pathlib.Path(sys.argv[1]).touch()'\n"
    "try:\n"
    "    run([sys.executable, '-c', touch, sys.argv[1]], backend=PtyBackend())\n"
    "except MissingExtra as error:\n"
    "    print(error.module)\n"
)


def test_a_pty_run_without_pyte_fails_before_the_program_is_started(tmp_path: Path):
    marker = tmp_path / "started"
    done = interpreter(PTY_RUN, str(marker), absent=("pyte",))
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "pyte"
    assert not marker.exists()  # без pyte вывод нечем разобрать, поэтому программу даже не запускали


@skip_on("linux", "pywinpty нужен только в Windows")
@skip_on("darwin", "pywinpty нужен только в Windows")
def test_a_pty_run_without_winpty_fails_before_the_program_is_started(tmp_path: Path):
    marker = tmp_path / "started"
    done = interpreter(PTY_RUN, str(marker), absent=("winpty",))
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "winpty"
    assert not marker.exists()
