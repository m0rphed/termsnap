"""
Поиск запускаемого файла: ищется по PATH из окружения запроса, а не нашего процесса.
"""

import os
import stat
import sys
from pathlib import Path

import pytest

from termsnap import Request
from termsnap.backends.executable import find_executable

NAME = "termsnap-sample-tool"


def install(directory: Path) -> Path:
    """
    Кладет в каталог запускаемый файл ``NAME`` (в Windows - командный файл, его находит PATHEXT).
    """
    directory.mkdir(exist_ok=True)
    path = directory / (NAME + (".bat" if sys.platform == "win32" else ""))
    path.write_text("@echo off\n" if sys.platform == "win32" else "#!/bin/sh\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def request(path: str | Path, name: str = NAME) -> Request:
    return Request(argv=(name,), env={"PATH": str(path)})


def test_program_is_found_in_the_path_of_the_request(tmp_path: Path):
    installed = install(tmp_path / "bin")
    assert Path(find_executable(request(tmp_path / "bin"))) == installed


def test_path_of_our_own_process_does_not_help(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    install(tmp_path / "ours")
    monkeypatch.setenv("PATH", str(tmp_path / "ours"))  # в PATH процесса программа есть, в PATH запроса - нет
    (tmp_path / "theirs").mkdir()
    with pytest.raises(FileNotFoundError, match=NAME):
        find_executable(request(tmp_path / "theirs"))


def test_directories_of_the_path_are_searched_in_order(tmp_path: Path):
    first, second = install(tmp_path / "first"), install(tmp_path / "second")
    path = os.pathsep.join([str(tmp_path / "first"), str(tmp_path / "second")])
    assert Path(find_executable(request(path))) == first
    assert Path(find_executable(request(os.pathsep.join(reversed(path.split(os.pathsep)))))) == second


def test_missing_program_is_reported_by_name(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match=NAME):
        find_executable(request(tmp_path))


def test_a_path_to_the_program_is_enough_without_the_path_variable(tmp_path: Path):
    installed = install(tmp_path / "bin")
    assert Path(find_executable(Request(argv=(str(installed),), env={}))) == installed
