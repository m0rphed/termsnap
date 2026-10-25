"""
Псевдотерминал в Linux и macOS: стандартные ``pty`` и ``subprocess``, сторонних пакетов не нужно.
"""

import contextlib
import fcntl
import os
import pty
import select
import signal
import struct
import subprocess
import termios
import time
from collections.abc import Callable

from termsnap.backends.pty.typist import Typist
from termsnap.errors import RunTimeout
from termsnap.request import Request
from termsnap.screen import Responder

#: Самое долгое ожидание вывода, секунд, пока идет сценарий: после него цикл проверяет, не пора ли печатать
#: следующий шаг или снимать экран.
POLL_INTERVAL = 0.02

#: Сколько байт читать за раз.
READ_SIZE = 65536


def stop_group(pid: int, kill: Callable[[int, int], None] = os.killpg) -> None:
    """
    Убивает группу процессов ``pid``. Группы уже нет (``ProcessLookupError``) или посылать сигнал нельзя
    (``PermissionError``: macOS, setuid-программы вроде ``top``) - не ошибка: закрытый конец терминала уже заставил
    ядро послать сеансу SIGHUP, этого хватает. ``kill`` подставляют тесты.
    """
    with contextlib.suppress(ProcessLookupError, PermissionError):
        kill(pid, signal.SIGKILL)


def run(executable: str, request: Request, stop: Callable[[int], None] = stop_group) -> tuple[bytes, int, bool]:
    """
    Запускает команду с терминалом нужного размера в отдельной сессии и возвращает весь вывод, код возврата и признак
    того, что программу остановили по ``Request.snapshot``. ``stop`` останавливает группу процессов по таймауту или
    снимку (тесты подставляют свою).
    """
    master, slave = pty.openpty()
    try:
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", request.rows, request.columns, 0, 0))
        process = subprocess.Popen(
            [executable, *request.argv[1:]],
            cwd=request.cwd,
            env=dict(request.env),
            stdin=slave,
            stdout=slave,
            stderr=slave,
            start_new_session=True,  # свой процесс-лидер: по таймауту останавливается вся группа
        )
    except BaseException:
        os.close(master)
        raise
    finally:
        os.close(slave)

    chunks: list[bytes] = []
    last_output = time.perf_counter()
    typist = Typist(request, started=last_output)
    responder = Responder(request.columns, request.rows)  # в отличие от ConPTY, сам pty на запросы не отвечает
    deadline = None if request.timeout is None else last_output + request.timeout
    timed_out = False
    stopped = False

    def output_text() -> str:
        return b"".join(chunks).decode("utf-8", errors="replace")

    # цикл: до дедлайна ->  напечатать готовый шаг сценария / снять экран, если пора ->
    #       ждать вывод (select) -> прочитать порцию, ответить на запросы терминала
    try:
        while True:
            now = time.perf_counter()
            remaining = None if deadline is None else deadline - now
            if remaining is not None and remaining <= 0:
                timed_out = True
                break
            if typist.watching:
                text = typist.next(now, last_output, output_text)
                if text is not None:
                    os.write(master, text.encode())
                if typist.snapshot_due(now, last_output, output_text):
                    stopped = True
                    break
                remaining = POLL_INTERVAL if remaining is None else min(remaining, POLL_INTERVAL)
            ready, _, _ = select.select([master], [], [], remaining)
            if not ready:
                continue
            try:
                data = os.read(master, READ_SIZE)
            except OSError:  # Linux: все копии конца терминала закрыты (EIO)
                break
            if not data:
                break
            chunks.append(data)
            last_output = time.perf_counter()
            reply = responder.feed(data)
            if reply:
                os.write(master, reply)
    finally:
        os.close(master)
        if timed_out or stopped:
            stop(process.pid)
        code = process.wait()
    output = b"".join(chunks)
    if timed_out:
        assert request.timeout is not None
        raise RunTimeout(request.argv, request.timeout, output)
    return output, code, stopped
