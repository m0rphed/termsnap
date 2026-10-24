"""
Запуск в псевдотерминале.

Файлы пакета: ``backend`` (``PtyBackend``, выбор платформы) -> ``conpty`` (Windows) и ``posix`` (Linux, macOS) ->
``typist`` (исполнение сценария, общее для обеих платформ). Платформенные модули и ``typist`` импортируются только
при запуске: им нужны ``pyte`` и ``pywinpty``, которых без ``termsnap[pty]`` нет.
"""

from termsnap.backends.pty.backend import PtyBackend

__all__ = ["PtyBackend"]
