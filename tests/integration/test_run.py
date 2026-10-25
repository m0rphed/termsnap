import os
import sys
from pathlib import Path

import pytest
from helpers import python

from termsnap import Indexed, PipeBackend, RunTimeout, Style, run


def test_run_captures_the_output():
    assert run(python("print('hello'); print('world')")).text == "hello\nworld"


def test_successful_command_is_ok_and_has_exit_code_zero():
    capture = run(python("pass"))
    assert (capture.ok, capture.returncode) == (True, 0)


def test_capture_remembers_the_command_and_how_long_it_took():
    capture = run(python("pass"))
    assert capture.argv[0] == sys.executable
    assert capture.duration >= 0


def test_failing_command_is_reported_not_raised():
    capture = run(python("import sys; print('boom'); sys.exit(3)"))
    assert (capture.ok, capture.returncode, capture.text) == (False, 3, "boom")


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


def test_a_custom_backend_can_be_used():
    from termsnap import Line, RawResult, Request, parse

    class Fake:
        def run(self, request: Request) -> RawResult:
            assert request.argv == ("fake", "arg")
            return RawResult(b"\x1b[32mgreen\n", 0, 0.5)

        def interpret(self, output: bytes, request: Request, encoding: str) -> tuple[Line, ...]:
            return parse(output.decode(encoding))

    capture = run(["fake", "arg"], backend=Fake())
    assert capture.text == "green"
    assert capture.lines[0].spans[0].style == Style(fg=Indexed(2))


def test_pipe_backend_is_the_default():
    assert run(python("print(1)"), backend=PipeBackend()).text == "1"


def test_capture_remembers_the_terminal_size():
    capture = run(python("print(1)"), columns=90, rows=20)
    assert (capture.columns, capture.rows) == (90, 20)
