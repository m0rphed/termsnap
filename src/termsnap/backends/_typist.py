"""
Сценарий в псевдотерминале: решает, когда печатать следующий шаг и когда снимать экран.

Общая часть для ConPTY и ``pty``: сами бэкенды только читают вывод, пишут то, что вернул ``Typist.next``, и
спрашивают ``Typist.snapshot_due``. Время передается снаружи, так что логику можно проверять без процессов.
"""

import re
from collections.abc import Callable

from termsnap import screen
from termsnap.backends.base import Request
from termsnap.steps import Pause, Snapshot, Step

#: Сколько секунд ждать первого вывода программы, которая молчит с самого начала, прежде чем печатать первый шаг.
SILENT_START = 1.0


class Typist:
    """
    Выполняет ``Request.input`` по шагам. Шаг печатается, когда выполнены условия:

    - после прошлого шага и после последнего вывода программы прошло не меньше ``settle`` секунд (при ``settle=0``
      это условие снимается: так нужно программам, которые перерисовывают экран постоянно и никогда не молчат);
    - если прошлым шагом была строка, программа что-то вывела в ответ (хотя бы повторила ввод): клавиши и паузы
      ответа не требуют;
    - если прошлым шагом была строка (или это начало) и задан ``prompt``, он виден в последней строке экрана, то есть
      программа снова ждет ввода.

    Первый шаг тоже ждет вывода: программа, которая еще запускается, может сбросить ввод, пришедший раньше (так
    делает ``tty.setcbreak``). Если программа молчит с самого начала, первый шаг уходит через ``SILENT_START``.
    """

    def __init__(self, request: Request, started: float) -> None:
        self._steps: list[Step] = list(request.input)
        self._prompt = None if request.prompt is None else re.compile(request.prompt)
        self._settle = request.settle
        self._columns = request.columns
        self._rows = request.rows
        self._snapshot: Snapshot | None = request.snapshot
        self._when = None if self._snapshot is None or self._snapshot.when is None else re.compile(self._snapshot.when)
        self._activity_at = started  # когда последний раз что-то напечатано или отсижена пауза
        self._awaits_reply = True  # первый шаг ждет первого вывода программы
        self._starting = True
        self._awaits_prompt = True
        self._resume_at: float | None = None
        self._matched_at: float | None = None
        self._checked_output_at: float | None = None

    @property
    def pending(self) -> bool:
        """
        Остались ли шаги, которые еще не выполнены.
        """
        return bool(self._steps)

    @property
    def watching(self) -> bool:
        """
        Нужно ли опрашивать ``Typist`` регулярно: есть невыполненные шаги или ждем момента снимка.
        """
        return bool(self._steps) or self._snapshot is not None

    def next(self, now: float, last_output: float, output: Callable[[], str]) -> str | None:
        """
        Текст, который нужно сейчас отправить программе, или ``None``, если время еще не пришло.

        ``last_output`` - момент последнего вывода программы (до первого вывода - момент запуска), ``output`` -
        весь вывод на сейчас; вызывается, только когда остальные условия выполнены.
        """
        while self._steps:
            step = self._steps[0]
            if isinstance(step, Pause):
                if self._resume_at is None:
                    self._resume_at = now + step.seconds
                if now < self._resume_at:
                    return None
                self._steps.pop(0)
                self._resume_at = None
                self._activity_at = now
                self._awaits_reply = self._awaits_prompt = self._starting = False
                continue
            if not self._ready(now, last_output, output):
                return None
            self._steps.pop(0)
            self._activity_at = now
            self._awaits_reply = self._awaits_prompt = isinstance(step, str)
            self._starting = False
            return step + "\r" if isinstance(step, str) else step.text
        return None

    def snapshot_due(self, now: float, last_output: float, output: Callable[[], str]) -> bool:
        """
        Пора ли снимать экран: шаги выполнены, ``when`` нашлось на экране, после этого прошло ``after`` секунд.
        """
        snapshot = self._snapshot
        if snapshot is None or self._steps:
            return False
        since = self._activity_at
        if self._when is not None:
            if self._matched_at is None and self._checked_output_at != last_output:
                self._checked_output_at = last_output
                if self._when.search(_screen_text(output(), self._columns, self._rows)):
                    self._matched_at = now
            if self._matched_at is None:
                return False
            since = max(since, self._matched_at)
        return now - since >= snapshot.after

    def _ready(self, now: float, last_output: float, output: Callable[[], str]) -> bool:
        if now - max(last_output, self._activity_at) < self._settle:
            return False
        silent_too_long = self._starting and now - self._activity_at >= SILENT_START
        if self._awaits_reply and last_output <= self._activity_at and not silent_too_long:
            return False
        if self._awaits_prompt and self._prompt is not None:
            lines = screen.render(output(), columns=self._columns, rows=self._rows)
            return bool(lines) and self._prompt.search(lines[-1].text.rstrip()) is not None
        return True


def _screen_text(output: str, columns: int, rows: int) -> str:
    return "\n".join(line.text for line in screen.render(output, columns=columns, rows=rows))
