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
