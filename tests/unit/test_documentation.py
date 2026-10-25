"""
Документация не расходится с кодом.
"""

from pathlib import Path

from registry import support_table

README = Path(__file__).resolve().parents[2] / "README.md"


def test_readme_holds_the_table_of_programs_by_system_that_the_tests_use():
    assert support_table() in README.read_text(encoding="utf-8"), (
        "таблица в README устарела: вставьте вместо нее вывод tests/registry.py:support_table()"
    )
