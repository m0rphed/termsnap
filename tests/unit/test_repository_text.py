"""
Текстовые файлы репозитория: одинаковые концы строк и ASCII-знаки в комментариях, docstring и документах.

Правила записаны тестом, а не словами в README, потому что их ломают незаметно: Windows-инструменты дописывают CR, а
редакторы подменяют дефис на типографское тире, которое ни найти, ни набрать. Каждый тест проходит по всем файлам и
называет все нарушения сразу.
"""

import ast
import io
import os
import tokenize
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: Каталоги, где лежит не наш текст: окружения, кэши, история, результаты запусков.
SKIPPED_DIRECTORIES = {
    ".git",
    ".jj",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "out",
    "node_modules",
}

TEXT_SUFFIXES = {".py", ".md", ".toml", ".yml", ".yaml", ".js", ".ini", ".1"}

#: Типографские знаки, которые в комментариях, docstring и документах заменяются ASCII: кавычки-елочки и лапки, длинные
#: тире, многоточие, стрелки.
TYPOGRAPHIC = set(
    "\N{LEFT-POINTING DOUBLE ANGLE QUOTATION MARK}\N{RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK}"
    "\N{EM DASH}\N{EN DASH}\N{HORIZONTAL ELLIPSIS}\N{RIGHTWARDS ARROW}\N{LEFTWARDS ARROW}"
    "\N{LEFT RIGHT ARROW}\N{LEFT DOUBLE QUOTATION MARK}\N{RIGHT DOUBLE QUOTATION MARK}"
    "\N{DOUBLE LOW-9 QUOTATION MARK}\N{LEFT SINGLE QUOTATION MARK}\N{RIGHT SINGLE QUOTATION MARK}"
)


def text_files() -> list[Path]:
    found = []
    for directory, subdirectories, names in os.walk(ROOT):
        # обход не заходит в окружения (.venv, .venv-ci-3.12) и кэши: они большие и не наши
        subdirectories[:] = [
            name for name in subdirectories if name not in SKIPPED_DIRECTORIES and not name.startswith(".venv")
        ]
        found += [Path(directory, name) for name in names if Path(name).suffix in TEXT_SUFFIXES or name == "Dockerfile"]
    return sorted(found)


def python_files() -> list[Path]:
    return [path for path in text_files() if path.suffix == ".py"]


def label(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def docstring_lines(source: str) -> set[int]:
    """
    Номера строк, которые занимают docstring модуля, классов и функций.
    """
    lines: set[int] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            first = node.body[0] if node.body else None
            text = first.value if isinstance(first, ast.Expr) else None
            if isinstance(text, ast.Constant) and isinstance(text.value, str):
                lines.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))
    return lines


def comment_lines(source: str) -> set[int]:
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return {token.start[0] for token in tokens if token.type == tokenize.COMMENT}


def typographic(path: Path, only_lines: set[int] | None = None) -> list[str]:
    """
    Типографские знаки в файле (в указанных строках, если они заданы): ``файл:строка: знак``.
    """
    return [
        f"{label(path)}:{number}: {char!r}"
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if only_lines is None or number in only_lines
        for char in line
        if char in TYPOGRAPHIC
    ]


def test_the_walk_finds_the_files_of_the_project():
    # защита от пустого обхода: проверки ниже, ничего не просмотрев, были бы зелеными зря
    assert len(python_files()) > 50
    assert {"README.md", "pyproject.toml", "ci.yml", "Dockerfile"} <= {path.name for path in text_files()}


def test_text_files_use_unix_line_endings():
    # ruff format приводит к LF файлы Python (line-ending в pyproject.toml), остальные правятся руками
    assert [label(path) for path in text_files() if b"\r" in path.read_bytes()] == []


def test_python_files_have_no_invisible_or_control_characters():
    # невидимые знаки (нулевой ширины, неразрывный пробел, управляющие) пишутся в строках через chr(...) или \N{...}
    found = [
        f"{label(path)}:{number}: U+{ord(char):04X}"
        for path in python_files()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        for char in line
        if char != "\t" and (unicodedata.category(char) in {"Cc", "Cf"} or char == "\N{NO-BREAK SPACE}")
    ]
    assert found == []


def test_comments_and_docstrings_have_no_typographic_characters():
    found = []
    for path in python_files():
        source = path.read_text(encoding="utf-8")
        found += typographic(path, comment_lines(source) | docstring_lines(source))
    assert found == []


def test_documents_and_configs_have_no_typographic_characters():
    found = [problem for path in text_files() if path.suffix != ".py" for problem in typographic(path)]
    assert found == []
