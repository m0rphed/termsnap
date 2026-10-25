"""
Нехватка необязательной зависимости: понятная ошибка с подсказкой, а не ModuleNotFoundError из глубины пакета.
"""

import pytest

from termsnap.errors import MissingExtra, TermsnapError
from termsnap.extras import need


def test_an_installed_module_passes_silently():
    need("json", "png", "Что-то")


def test_a_missing_module_is_reported_with_the_extra_to_install():
    with pytest.raises(MissingExtra) as caught:
        need("module_that_does_not_exist", "png", "Рисование в PNG")
    error = caught.value
    assert (error.module, error.extra) == ("module_that_does_not_exist", "png")
    assert str(error) == (
        "Рисование в PNG: не установлен модуль module_that_does_not_exist. Поставьте набор: pip install termsnap[png]"
    )


def test_the_error_is_both_a_termsnap_error_and_an_import_error():
    with pytest.raises(MissingExtra) as caught:
        need("module_that_does_not_exist", "pty", "Запуск")
    assert isinstance(caught.value, TermsnapError)
    assert isinstance(caught.value, ImportError)


def test_the_original_import_error_stays_as_the_cause():
    with pytest.raises(MissingExtra) as caught:
        need("module_that_does_not_exist", "pty", "Запуск")
    assert isinstance(caught.value.__cause__, ModuleNotFoundError)
