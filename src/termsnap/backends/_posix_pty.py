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

from termsnap.backends.base import Request
from termsnap.errors import RunTimeout


def run(executable: str, request: Request) -> tuple[bytes, int]:
    """
    Запускает команду с терминалом нужного размера в отдельной сессии и возвращает весь вывод и код возврата.
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
    deadline = None if request.timeout is None else time.monotonic() + request.timeout
    timed_out = False
    try:
        while True:
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                timed_out = True
                break
            ready, _, _ = select.select([master], [], [], remaining)
            if not ready:
                timed_out = True
                break
            try:
                data = os.read(master, 65536)
            except OSError:  # Linux: все копии конца терминала закрыты (EIO)
                break
            if not data:
                break
            chunks.append(data)
    finally:
        os.close(master)
        if timed_out:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
        code = process.wait()
    output = b"".join(chunks)
    if timed_out:
        assert request.timeout is not None
        raise RunTimeout(request.argv, request.timeout, output)
    return output, code
