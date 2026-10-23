"""
Способы запуска команд.
"""

from termsnap.backends.base import Backend, RawResult, Request
from termsnap.backends.pipe import PipeBackend

__all__ = ["Backend", "PipeBackend", "RawResult", "Request"]
