"""
Способы запуска команд.
"""

from termsnap.backends.base import Backend, RawResult, Request
from termsnap.backends.pipe import PipeBackend
from termsnap.backends.pty import PtyBackend

__all__ = ["Backend", "PipeBackend", "PtyBackend", "RawResult", "Request"]
