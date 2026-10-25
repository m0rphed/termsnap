"""
Нехватка зависимости: в строгом режиме (CI) это ошибка, в обычном - пропуск с причиной.
"""

import pytest
import support


def test_in_strict_mode_a_missing_dependency_is_an_error_with_a_hint(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(support, "STRICT", True)
    with pytest.raises(pytest.fail.Exception, match=r"нет шрифта. Поставьте шрифт"):
        support.missing("нет шрифта", "Поставьте шрифт")


def test_in_ordinary_mode_a_missing_dependency_is_a_skip_with_the_reason(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(support, "STRICT", False)
    with pytest.raises(pytest.skip.Exception, match=r"нет шрифта \(Поставьте шрифт\)"):
        support.missing("нет шрифта", "Поставьте шрифт")


def test_an_installed_module_is_returned():
    assert support.require_module("json").dumps([1]) == "[1]"


def test_a_module_that_is_not_installed_is_reported_by_name(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(support, "STRICT", True)
    with pytest.raises(pytest.fail.Exception, match="module_that_does_not_exist"):
        support.require_module("module_that_does_not_exist")


def test_a_platform_skip_carries_the_marker_that_strict_mode_accepts():
    mark = support.skip_on("no-such-platform", "причина")
    assert mark.mark.kwargs["reason"] == f"{support.EXPECTED_SKIP}: причина"
