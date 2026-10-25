"""
Версии чужих пакетов, под которые записаны ожидания, совпадают с установленными и с ``uv.lock``.
"""

import re
import subprocess
import tomllib
from importlib import metadata
from pathlib import Path

import pytest
from pins import GIT_VERIFIED, PINNED
from registry import NODE

LOCK = Path(__file__).resolve().parents[2] / "uv.lock"

ADVICE = (
    "Ожидания в tests/external записаны под {pinned}, а стоит {found}. Если версию меняли нарочно: прогоните "
    "`python ci/run.py test --level external`, поправьте расхождения и обновите tests/pins.py. Если нет: "
    "`uv sync --locked`."
)


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


@pytest.mark.parametrize("name", PINNED)
def test_installed_version_is_the_one_the_expectations_were_written_for(name: str):
    found = metadata.version(name)
    assert found == PINNED[name], ADVICE.format(pinned=PINNED[name], found=f"{name} {found}")


def test_node_is_the_pinned_version_and_not_the_one_from_the_system():
    version = subprocess.run([NODE, "--version"], capture_output=True, text=True, check=True).stdout.strip()
    assert version == f"v{PINNED['nodejs-wheel-binaries']}"


def test_git_is_on_a_line_of_versions_the_expectations_were_checked_on():
    output = subprocess.run(["git", "--version"], capture_output=True, text=True, check=True).stdout
    line = ".".join(re.search(r"(\d+)\.(\d+)", output).groups())
    assert line in GIT_VERIFIED, (
        f"git {line}: ожидания к git_history проверены на {GIT_VERIFIED}. Прогоните `python ci/run.py test --level "
        "external` на этой версии и, если зелено, добавьте ее в tests/pins.py:GIT_VERIFIED."
    )


def test_lock_file_holds_the_same_versions():
    locked = {
        normalized(package["name"]): package["version"] for package in tomllib.loads(LOCK.read_text("utf-8"))["package"]
    }
    assert {name: locked.get(normalized(name)) for name in PINNED} == PINNED, ADVICE.format(
        pinned=PINNED, found="другие версии в uv.lock"
    )
