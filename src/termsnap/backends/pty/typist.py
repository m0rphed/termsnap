"""
Исполнитель сценария в псевдотерминале: решает, когда печатать следующий шаг и когда снимать экран.

Общая часть для ConPTY и ``pty``: сами бэкенды только читают вывод, пишут то, что вернул ``Typist.next``, и
спрашивают ``Typist.snapshot_due``. Время передается снаружи, так что логику можно проверять без процессов.
"""

import re
from collections.abc import Callable

from termsnap.request import Request
from termsnap.scenario import Key, Pause, Snapshot, Step
from termsnap.screen import render

#: Сколько секунд ждать первого вывода программы, которая молчит с самого начала, прежде чем печатать первый шаг.
SILENT_START = 1.0

#: Откуда брать текст вывода по требованию: вызывается, только когда он нужен (разбор экрана дорогой).
type OutputText = Callable[[], str]


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

    Состояние - это "чего мы сейчас ждем": ответа на прошлую строку (``_awaits_reply``), приглашения
    (``_awaits_prompt``), окончания паузы (``_resume_at``) или первого вывода (``_starting``).
    """

    def __init__(self, request: Request, started: float) -> None:
        self._steps: list[Step] = list(request.input)
        self._settle = request.settle
        self._prompt = None if request.prompt is None else re.compile(request.prompt)
        self._columns = request.columns
        self._rows = request.rows
        self._visible_only = request.capture_visible_only
        self._snapshot: Snapshot | None = request.snapshot
        self._when = None if self._snapshot is None or self._snapshot.when is None else re.compile(self._snapshot.when)

        self._activity_at = started  # когда последний раз что-то напечатано или отсижена пауза
        self._starting = True  # еще ничего не напечатано: первый шаг ждет первого вывода программы
        self._awaits_reply = True
        self._awaits_prompt = True
        self._resume_at: float | None = None  # когда закончится текущая пауза
        self._matched_at: float | None = None  # когда на экране впервые нашлось ``Snapshot.when``
        self._checked_output_at: float | None = None  # на каком выводе искали ``when`` в последний раз

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

    def next(self, now: float, last_output: float, output: OutputText) -> str | None:
        """
        Текст, который нужно сейчас отправить программе, или ``None``, если время еще не пришло.

        ``last_output`` - момент последнего вывода программы (до первого вывода - момент запуска), ``output`` -
        весь вывод на сейчас; вызывается, только когда остальные условия выполнены.
        """
        # пока есть шаги:
        #     пауза  -> дождаться ее конца; потом забыть, что чего-то ждали, и взять следующий шаг
        #     иначе  -> если еще не готовы, выйти с None; готовы - отдать текст шага
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
            if not self._is_ready(now, last_output, output):
                return None
            self._steps.pop(0)
            self._activity_at = now
            self._awaits_reply = self._awaits_prompt = isinstance(step, str)  # ответ и приглашение - после строки
            self._starting = False
            return step + Key.ENTER.text if isinstance(step, str) else step.text
        return None

    def snapshot_due(self, now: float, last_output: float, output: OutputText) -> bool:
        """
        Пора ли снимать экран: шаги выполнены, ``when`` нашлось на экране, после этого прошло ``after`` секунд.
        """
        snapshot = self._snapshot
        if snapshot is None or self._steps:
            return False
        since = self._activity_at
        if self._when is not None:
            if self._matched_at is None and self._checked_output_at != last_output:
                # экран разбирается заново только когда вывод изменился, иначе опрос каждые 20 мс был бы слишком дорог
                self._checked_output_at = last_output
                if self._when.search(self._screen_text(output())):
                    self._matched_at = now
            if self._matched_at is None:
                return False
            since = max(since, self._matched_at)
        return now - since >= snapshot.after

    def _is_ready(self, now: float, last_output: float, output: OutputText) -> bool:
        """
        Можно ли печатать очередной шаг: вывод помолчал, программа ответила на прошлую строку, виден prompt.
        """
        if now - max(last_output, self._activity_at) < self._settle:
            return False
        silent_too_long = self._starting and now - self._activity_at >= SILENT_START
        if self._awaits_reply and last_output <= self._activity_at and not silent_too_long:
            return False
        if self._awaits_prompt and self._prompt is not None:
            lines = render(output(), columns=self._columns, rows=self._rows)
            return bool(lines) and self._prompt.search(lines[-1].text.rstrip()) is not None
        return True

    def _screen_text(self, output: str) -> str:
        """
        Текст экрана (или его видимой части, если так задано) для поиска ``Snapshot.when``.
        """
        lines = render(output, columns=self._columns, rows=self._rows, visible_only=self._visible_only)
        return "\n".join(line.text for line in lines)
