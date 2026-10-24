"""
Псевдотерминал в Windows: ConPTY через ``pywinpty``.

ConPTY закрывает канал вывода не сразу после выхода программы (``read`` возвращает конец потока примерно через
5 секунд, закрытие терминала это не ускоряет), поэтому завершение определяется по самому процессу, а после него
ждется короткая тишина в выводе.
"""

import time
from threading import Thread

from winpty import PtyProcess

from termsnap.backends._typist import Typist
from termsnap.backends.base import Request
from termsnap.errors import RunTimeout

#: Сколько вывод должен молчать после завершения процесса, чтобы считать его полностью прочитанным, секунд.
_QUIET = 0.3
_POLL = 0.01


def run(executable: str, request: Request) -> tuple[bytes, int, bool]:
    """
    Запускает команду в ConPTY и возвращает весь вывод (в UTF-8), код возврата и признак того, что программу
    остановили по ``Request.snapshot``.
    """
    process = PtyProcess.spawn(
        [executable, *request.argv[1:]],
        cwd=None if request.cwd is None else str(request.cwd),
        env=dict(request.env),
        dimensions=(request.rows, request.columns),
    )
    chunks: list[str] = []
    last_output = time.monotonic()
    typist = Typist(request, started=last_output)

    def pump() -> None:
        nonlocal last_output
        while True:
            try:
                chunks.append(process.read(65536))
            except (EOFError, OSError):
                return
            last_output = time.monotonic()

    # поток-демон: он может дожить до закрытия канала уже после возврата из функции
    Thread(target=pump, daemon=True).start()
    deadline = None if request.timeout is None else time.monotonic() + request.timeout
    while True:
        now = time.monotonic()
        if deadline is not None and now >= deadline:
            process.terminate(force=True)
            assert request.timeout is not None
            raise RunTimeout(request.argv, request.timeout, "".join(chunks).encode())
        alive = process.isalive()
        if not alive and now - last_output >= _QUIET:
            break
        if alive and typist.watching:
            text = typist.next(now, last_output, lambda: "".join(chunks))
            if text is not None:
                process.write(text)
            if typist.snapshot_due(now, last_output, lambda: "".join(chunks)):
                output = "".join(chunks).encode()
                process.terminate(force=True)
                process.close()
                return output, -1, True
        time.sleep(_POLL)
    code = process.exitstatus
    process.close()
    return "".join(chunks).encode(), -1 if code is None else code, False
