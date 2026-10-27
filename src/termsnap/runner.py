"""
Главная функция библиотеки - ``run``: собирает запрос, отдает его бэкенду и разбирает вывод.
"""

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from termsnap.backends import Backend, PipeBackend
from termsnap.capture import Capture
from termsnap.defaults import DEFAULT_COLUMNS, DEFAULT_ROWS, DEFAULT_SETTLE, DEFAULT_TIMEOUT
from termsnap.environment import terminal_environment
from termsnap.request import Request
from termsnap.scenario import Snapshot, Step


def run(
    argv: Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    extra_env: Mapping[str, str] | None = None,
    timeout: float | None = DEFAULT_TIMEOUT,
    color: bool = True,
    columns: int = DEFAULT_COLUMNS,
    rows: int = DEFAULT_ROWS,
    encoding: str = "utf-8",
    backend: Backend | None = None,
    input: Sequence[Step] = (),
    prompt: str | None = None,
    settle: float = DEFAULT_SETTLE,
    snapshot: Snapshot | None = None,
    capture_visible_only: bool = False,
) -> Capture:
    """
    Запускает команду (без оболочки: ``["node", "app.js"]``) и возвращает ее вывод со стилями.

    Окружение процесса складывается из трех слоев (подробнее в ``terminal_environment``): ``env`` - исходное окружение
    целиком (по умолчанию окружение текущего процесса, как у ``subprocess.run``: переданный ``env`` заменяет его,
    а не дополняет), поверх него ``extra_env`` - переменные, которые нужно добавить или заменить, остальные остаются
    (``extra_env={"NODE_ENV": "test"}``), и поверх всего переменные терминала, которые назначает termsnap: ``TERM``,
    ``COLUMNS``, ``LINES``, UTF-8 для Python и цвет (``color``). Переменные последнего слоя в ``extra_env`` задавать
    нельзя - будет ``ValueError``. ``encoding`` - кодировка вывода программы; нераспознанные байты
    заменяются символом подстановки. По умолчанию команда запускается через каналы (``PipeBackend``); для программ,
    которым нужен терминал, есть ``PtyBackend``.

    Сценарий для интерактивных программ (только ``PtyBackend``, см. ``termsnap.scenario``): ``input`` - шаги: строка
    печатается с Enter (команды REPL), ``Keys``/``Key`` - клавиши без Enter, ``Pause`` - ожидание. Шаг выполняется,
    когда вывод молчит ``settle`` секунд (``settle=0`` - не ждать, для программ с постоянной перерисовкой) и после
    строки на экране виден ``prompt`` (регулярное выражение для последней строки, например ``r"In \\[\\d+\\]:$"``).
    Когда программа сама не завершается (``htop``), ``snapshot`` задает момент снимка экрана: после него программа
    останавливается, а в ``Capture.stopped`` стоит ``True``. Иначе программа должна завершиться сама (``exit``),
    а если нет - ``RunTimeout`` с тем, что успело появиться.

    ``capture_visible_only`` (только ``PtyBackend``): по умолчанию в результат входят и строки, ушедшие вверх
    при прокрутке экрана, чтобы не терять длинный вывод. С ``True`` берется только то, что видно на экране в
    конце (``rows`` строк), как на скриншоте окна терминала; так же ``Snapshot(when=...)`` ищет текст только
    среди видимого. Программам, которые рисуют экран целиком, это обычно и нужно.
    """
    command = tuple(argv)
    if not command:
        raise ValueError("команда пуста")
    request = Request(
        argv=command,
        env=terminal_environment(
            os.environ if env is None else env,
            color=color,
            columns=columns,
            rows=rows,
            extra=extra_env,
        ),
        cwd=None if cwd is None else Path(cwd),
        timeout=timeout,
        columns=columns,
        rows=rows,
        input=tuple(input),
        prompt=prompt,
        settle=settle,
        snapshot=snapshot,
        capture_visible_only=capture_visible_only,
    )

    backend = backend or PipeBackend()
    result = backend.run(request)  # байты вывода, код возврата, время
    lines = backend.interpret(result.output, request, encoding)  # строки со стилями: у каждого бэкенда свой разбор

    return Capture(
        command,
        result.returncode,
        result.duration,
        result.output,
        lines,
        columns,
        rows,
        result.stopped,
    )
