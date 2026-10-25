"""
Эмуляция экрана терминала на ``pyte``: вывод программы, запущенной в псевдотерминале, превращается в те же строки
со стилями (``Line``), что и у разбора ``termsnap.ansi``, но экран ведется целиком: абсолютные позиции курсора,
прокрутка, перерисовка кадров, стирание областей.

Нужен дополнительный пакет ``pyte`` (``pip install termsnap[pty]``).

Отличия от "голого" ``pyte``: сохраняется индекс цвета палитры (``Indexed``, а не готовый RGB), поэтому тема
остается в силе, и поддерживается "тусклый" атрибут (SGR 2), который ``pyte`` отбрасывает.

Файлы пакета: ``emulator`` (экран pyte с поправками) -> ``convert`` (ячейки -> модель) -> ``rendering`` (``render``);
``responder`` отвечает на запросы программы и экран не показывает.
"""

from termsnap.extras import need

need("pyte", "pty", "Эмуляция экрана терминала")

from termsnap.screen.rendering import HISTORY_LINES, render
from termsnap.screen.responder import Responder

__all__ = ["HISTORY_LINES", "Responder", "render"]
