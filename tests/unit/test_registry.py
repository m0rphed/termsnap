"""
Правила, по которым тесты решают, запускать ли чужую программу: исключенную на этой системе пропускают с причиной, а
обязательную, которой нет, считают ошибкой.
"""

import sys

import pytest
from registry import SYSTEMS, Program, require

HERE = sys.platform


def program(**options) -> Program:
    return Program("sample", ("sample",), **options)


def test_a_program_that_is_not_expected_here_is_skipped_with_the_reason_from_the_table():
    with pytest.raises(pytest.skip.Exception, match="sample: нет такой на этой системе"):
        require(program(tool="no-such-tool-anywhere", absent={HERE: "нет такой на этой системе"}))


def test_a_required_program_that_is_missing_is_an_error_and_not_a_skip():
    with pytest.raises(pytest.fail.Exception, match="no-such-tool-anywhere"):
        require(program(tool="no-such-tool-anywhere"))


def test_a_program_that_is_found_is_just_run():
    require(program(tool="python" if sys.platform == "win32" else "sh"))


def test_a_program_without_a_system_tool_needs_nothing_from_the_system():
    require(program())


def test_exclusions_for_other_systems_do_not_matter_here():
    other = next(name for name in SYSTEMS if name != HERE)
    require(program(absent={other: "только там"}))
