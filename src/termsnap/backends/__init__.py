"""
Способы запуска команд.

- ``PipeBackend`` - каналы, только стандартная библиотека; вывод разбирает ``termsnap.ansi``.
- ``PtyBackend`` - псевдотерминал (``termsnap[pty]``); экран ведет эмулятор ``termsnap.screen``, умеет вводить
  текст по сценарию (``termsnap.scenario``).
"""

from termsnap.backends.base import Backend
from termsnap.backends.pipe import PipeBackend
from termsnap.backends.pty import PtyBackend
from termsnap.request import RawResult, Request

__all__ = ["Backend", "PipeBackend", "PtyBackend", "RawResult", "Request"]
