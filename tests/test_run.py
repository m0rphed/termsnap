import os
import sys
from pathlib import Path

import pytest

from termsnap import Indexed, PipeBackend, RunTimeout, Style, run, terminal_environment


def python(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def test_run_captures_output_and_exit_code():
    capture = run(python("print('hello'); print('world')"))
    assert capture.ok
    assert capture.returncode == 0
    assert capture.text == "hello\nworld"
    assert capture.argv[0] == sys.executable
    assert capture.duration >= 0


def test_failing_command_is_reported_not_raised():
    capture = run(python("import sys; print('boom'); sys.exit(3)"))
    assert not capture.ok
    assert capture.returncode == 3
    assert capture.text == "boom"


def test_stderr_is_merged_with_stdout_in_order():
    code = "import sys; print('a', flush=True); print('b', file=sys.stderr, flush=True); print('c', flush=True)"
    assert run(python(code)).text == "a\nb\nc"


def test_ansi_output_becomes_styled_spans():
    capture = run(python("print('\\x1b[31mred\\x1b[0m ok')"))
    first, second = capture.lines[0].spans
    assert (first.text, first.style) == ("red", Style(fg=Indexed(1)))
    assert second.text == " ok"


def test_raw_bytes_are_kept():
    assert run(python("print('\\x1b[1mx')")).output.startswith(b"\x1b[1mx")


def test_color_is_forced_on_by_default_and_can_be_turned_off():
    code = "import os; print(os.environ.get('FORCE_COLOR'), os.environ.get('NO_COLOR'))"
    assert run(python(code)).text == "1 None"
    assert run(python(code), color=False).text == "None 1"


def test_terminal_variables_reach_the_process():
    code = "import os; print(os.environ['TERM'], os.environ['COLUMNS'], os.environ['LINES'])"
    assert run(python(code), columns=80, rows=24).text == "xterm-256color 80 24"


def test_cwd_is_used(tmp_path: Path):
    assert run(python("import os; print(os.getcwd())"), cwd=tmp_path).text == str(tmp_path.resolve())


def test_custom_environment_replaces_the_current_one():
    env = {key: value for key, value in os.environ.items() if key in {"PATH", "SYSTEMROOT"}} | {"MY_VAR": "42"}
    assert run(python("import os; print(os.environ['MY_VAR'])"), env=env).text == "42"


def test_utf8_output_is_decoded_even_when_the_console_is_not_utf8():
    assert run(python("print('Привет')")).text == "Привет"


def test_other_encoding_can_be_requested():
    code = "import sys; sys.stdout.buffer.write('Привет'.encode('cp866'))"
    assert run(python(code), encoding="cp866").text == "Привет"


def test_invalid_bytes_are_replaced():
    assert run(python("import sys; sys.stdout.buffer.write(b'a\\xffb')")).text == "a\ufffdb"


def test_no_input_is_available():
    code = "import sys; print(repr(sys.stdin.read()))"
    assert run(python(code)).text == "''"


def test_timeout_stops_the_process_and_keeps_partial_output():
    with pytest.raises(RunTimeout) as caught:
        run(python("import time; print('start', flush=True); time.sleep(60)"), timeout=1.0)
    assert caught.value.output.startswith(b"start")
    assert caught.value.timeout == 1.0


def test_missing_program_raises_file_not_found():
    with pytest.raises(FileNotFoundError, match="no-such-program-termsnap"):
        run(["no-such-program-termsnap"])


def test_empty_command_is_rejected():
    with pytest.raises(ValueError, match="пуста"):
        run([])


def test_terminal_environment_overrides_color_variables_of_the_base():
    base = {"NO_COLOR": "1", "FORCE_COLOR": "0", "KEEP": "yes"}
    env = terminal_environment(base, color=True, columns=100, rows=30)
    assert "NO_COLOR" not in env
    assert env["FORCE_COLOR"] == "1"
    assert env["KEEP"] == "yes"


def test_a_custom_backend_can_be_used():
    from termsnap import RawResult, Request

    class Fake:
        def run(self, request: Request) -> RawResult:
            assert request.argv == ("fake", "arg")
            return RawResult(b"\x1b[32mgreen\n", 0, 0.5)

    capture = run(["fake", "arg"], backend=Fake())
    assert capture.text == "green"
    assert capture.lines[0].spans[0].style == Style(fg=Indexed(2))


def test_pipe_backend_is_the_default():
    assert run(python("print(1)"), backend=PipeBackend()).text == "1"
