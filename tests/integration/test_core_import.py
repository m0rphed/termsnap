"""
Ядро пакета в чистом интерпретаторе: импорт не тянет необязательные зависимости.
"""

import subprocess
import sys


def test_core_import_does_not_pull_optional_dependencies():
    code = (
        "import sys, termsnap, termsnap.backends\n"
        "loaded = {name for name in ('PIL', 'pyte', 'winpty') if name in sys.modules}\n"
        "assert not loaded, loaded\n"
    )
    done = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
