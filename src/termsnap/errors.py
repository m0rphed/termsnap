"""
Ошибки termsnap.
"""


class TermsnapError(Exception):
    """
    Базовая ошибка библиотеки.
    """


class RunTimeout(TermsnapError):
    """
    Команда не завершилась за отведенное время и была остановлена; ``output`` - то, что она успела вывести.
    """

    def __init__(self, argv: tuple[str, ...], timeout: float, output: bytes) -> None:
        super().__init__(f"команда {' '.join(argv)!r} не завершилась за {timeout} с")
        self.argv = argv
        self.timeout = timeout
        self.output = output


class MissingExtra(TermsnapError, ImportError):
    """
    Не установлена необязательная зависимость, нужная для запрошенного действия: ``extra`` - название набора
    (``pip install termsnap[extra]``), ``module`` - что не импортируется. Это и ``ImportError``, поэтому ее можно
    ловить как обычную нехватку модуля.
    """

    def __init__(self, module: str, extra: str, purpose: str) -> None:
        super().__init__(f"{purpose}: не установлен модуль {module}. Поставьте набор: pip install termsnap[{extra}]")
        self.module = module
        self.extra = extra


class FontNotFound(TermsnapError):
    """
    Не нашлось шрифта, пригодного для рисования: ни одно из запрошенных семейств не установлено или не содержит
    нужных символов. ``problems`` - по строке на каждое проверенное семейство с причиной отказа.
    """

    def __init__(self, problems: list[str]) -> None:
        super().__init__("подходящий моноширинный шрифт не найден:\n  " + "\n  ".join(problems))
        self.problems = problems
