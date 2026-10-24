"""
Ответы терминала на запросы программы.
"""

import codecs

import pyte

from termsnap.screen.emulator import TerminalScreen


class Responder:
    """
    Живой терминал, который только отвечает программе: вывод подается по мере появления, а в ответ возвращаются
    байты, которые настоящий терминал отправил бы на вход программы (позиция курсора на ``ESC[6n``, тип терминала
    на ``ESC[c``). Без ответа библиотеки вроде ``prompt_toolkit`` (IPython) пишут, что терминал не поддерживает
    запрос позиции курсора, и работают хуже. Нужен там, где псевдотерминал сам не отвечает (Linux и macOS; ConPTY
    в Windows отвечает сам, второй ответ только засорил бы ввод).
    """

    def __init__(self, columns: int, rows: int) -> None:
        self._screen = TerminalScreen(columns, rows, history=1)  # история не нужна: важны только ответы
        self._stream = pyte.Stream(self._screen)
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")  # порция может оборваться в символе

    def feed(self, data: bytes) -> bytes:
        """
        Принимает очередную порцию вывода (в том числе обрезанную посреди символа) и возвращает ответы на запросы.
        """
        self._stream.feed(self._decoder.decode(data))
        reply = "".join(self._screen.replies)
        self._screen.replies.clear()
        return reply.encode()
