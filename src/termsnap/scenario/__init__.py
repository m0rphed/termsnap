"""
Сценарий для интерактивной программы: что напечатать, чего подождать и когда снимать экран.

    run(["htop"], backend=PtyBackend(), input=[Key.DOWN, Key.DOWN, Pause(1)], snapshot=Snapshot(after=2))

В ``input`` обычная строка печатается с Enter, ``Keys`` - как есть (без Enter), ``Key`` - готовые клавиши,
``Pause`` - просто ждет.

Здесь только описание сценария. Исполняет его ``Typist`` из ``termsnap.backends.pty`` (он нужен только
псевдотерминалу и тянет эмулятор экрана).
"""

from termsnap.scenario.keys import Key, Keys
from termsnap.scenario.steps import Pause, Snapshot, Step

__all__ = ["Key", "Keys", "Pause", "Snapshot", "Step"]
