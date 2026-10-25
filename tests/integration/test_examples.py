"""
Примеры из ``examples`` работают: каждый запускается как есть, завершается без ошибки и оставляет картинки PNG.

Примеры - это то, что читают люди, поэтому они не должны устаревать вместе с библиотекой. Что именно рисуется на
картинках, проверяют тесты рисования; здесь важно, что пример выполнился и дал настоящие PNG.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from helpers import PNG_SIGNATURE
from support import require_module, require_pty_extras

require_module("PIL")
require_pty_extras()

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"

#: Примеры по имени файла и числу картинок, которые каждый оставляет.
SCRIPTS = {
    "01_capture_a_command.py": 1,
    "02_interactive_session.py": 1,
    "03_snapshot_of_a_running_program.py": 1,
    "04_themes_and_fonts.py": 4,
    "gallery.py": 5,  # по картинке на каждую программу витрины
}


@pytest.mark.parametrize(("script", "pictures"), SCRIPTS.items(), ids=list(SCRIPTS))
def test_example_runs_and_leaves_png_pictures(script: str, pictures: int, tmp_path: Path, system_fonts):
    arguments = ["--out", str(tmp_path)] if script == "gallery.py" else [str(tmp_path)]
    done = subprocess.run(
        [sys.executable, "-X", "utf8", str(EXAMPLES / script), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    files = sorted(tmp_path.glob("*.png"))
    assert len(files) == pictures, [file.name for file in files]
    assert all(file.read_bytes().startswith(PNG_SIGNATURE) for file in files)


def test_every_example_is_listed_here():
    # новый пример без теста быстро перестанет работать: его нужно добавить в SCRIPTS
    written = {path.name for path in EXAMPLES.glob("*.py")}
    assert written == set(SCRIPTS)
