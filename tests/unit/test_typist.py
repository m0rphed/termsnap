"""
Логика сценария без процессов: время и вывод программы задаются вручную.
"""

import pytest
from support import require_module

require_module("pyte")

from termsnap import Key, Keys, Pause, Request, Snapshot, Step
from termsnap.backends.pty.typist import Typist

PROMPT = r">>$"


def typist(*steps: Step, prompt: str | None = None, settle: float = 0.5, snapshot: Snapshot | None = None, at=0.0):
    request = Request(argv=("x",), env={}, input=steps, prompt=prompt, settle=settle, snapshot=snapshot)
    return Typist(request, started=at)


def silent() -> str:
    return ""


class CountedScreen:
    """
    Текст экрана программы, который считает свои чтения. Экран разбирает эмулятор, это дорого, и ``Typist`` обязан
    читать его не чаще, чем нужно (контракт по скорости, а не по поведению): пока вывод идет, не читать вовсе.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self.reads = 0

    def __call__(self) -> str:
        self.reads += 1
        return self.text


# --- строки ---


def test_first_step_waits_for_output_and_then_for_silence():
    t = typist("a")
    assert t.next(0.2, 0.1, silent) is None  # вывод только что был
    assert t.next(0.7, 0.1, silent) == "a\r"
    assert not t.pending


def test_first_step_does_not_go_before_the_program_has_printed_anything():
    t = typist("a")
    assert t.next(0.9, 0.0, silent) is None  # программа еще запускается и может сбросить ввод
    assert t.next(1.0, 0.0, silent) == "a\r"  # молчит с самого начала - ждать вывода бесполезно


def test_next_line_waits_for_a_reply_and_then_for_silence():
    t = typist("a", "b")
    assert t.next(1.0, 0.1, silent) == "a\r"
    assert t.next(5.0, 0.0, silent) is None  # ответа не было: ни эха, ни результата
    assert t.next(1.3, 1.1, silent) is None  # ответ идет
    assert t.next(1.7, 1.1, silent) == "b\r"
    assert t.next(9.0, 1.1, silent) is None
    assert not t.pending


def test_prompt_is_looked_for_on_the_last_screen_line():
    t = typist("a", prompt=PROMPT)
    assert t.next(1.0, 0.1, lambda: "первая\r\n\x1b[32m>> \x1b[0m") == "a\r"


def test_the_screen_is_not_read_while_the_output_is_still_coming():
    screen = CountedScreen(">> ")
    t = typist("a", prompt=PROMPT)
    assert t.next(0.1, 0.0, screen) is None
    assert screen.reads == 0


def test_prompt_with_typed_text_is_not_a_prompt_to_wait_for():
    t = typist("a", "b", prompt=PROMPT)
    assert t.next(1.0, 0.1, lambda: ">> ") == "a\r"
    assert t.next(2.0, 1.5, lambda: ">> a") is None  # введенное эхом, ответа еще нет
    assert t.next(3.0, 2.5, lambda: ">> a\r\n5\r\n>> ") == "b\r"


def test_empty_screen_is_not_a_prompt():
    assert typist("a", prompt=r".*").next(1.0, 0.1, silent) is None


def test_settle_zero_does_not_wait_for_silence_but_still_waits_for_a_reply():
    t = typist("a", "b", settle=0)
    assert t.next(0.1, 0.1, silent) == "a\r"  # вывод идет прямо сейчас, и это не мешает
    assert t.next(0.2, 0.1, silent) is None  # на строку еще не ответили
    assert t.next(0.3, 0.25, silent) == "b\r"


# --- клавиши и паузы ---


def test_keys_go_as_they_are_without_enter_and_need_no_reply():
    t = typist(Keys("ab"), Key.UP, Key.ENTER)
    assert t.next(1.0, 0.1, silent) == "ab"
    assert t.next(1.2, 0.0, silent) is None  # settle отсчитывается и от нажатия
    assert t.next(1.6, 0.0, silent) == "\x1b[A"  # ответа не было, и ждать его не нужно
    assert t.next(2.2, 0.0, silent) == "\r"
    assert not t.pending


def test_partial_line_does_not_wait_for_a_clean_prompt():
    t = typist(Keys("pri"), "x", prompt=PROMPT)
    assert t.next(1.0, 0.1, lambda: ">> ") == "pri"
    assert t.next(2.0, 0.0, lambda: ">> pri") == "x\r"  # введена часть строки: приглашение уже не "чистое"


def test_prompt_and_reply_are_awaited_again_after_a_line_even_before_keys():
    t = typist("a", Key.UP, prompt=PROMPT)
    assert t.next(1.0, 0.1, lambda: ">> ") == "a\r"
    assert t.next(2.0, 1.5, lambda: ">> a") is None
    assert t.next(2.0, 1.5, lambda: ">> a\r\n>> ") == "\x1b[A"


def test_pause_waits_a_fixed_time_and_then_settle():
    t = typist(Pause(2), "a")
    assert t.next(0.0, 0.0, silent) is None
    assert t.next(1.9, 0.0, silent) is None
    assert t.next(2.1, 0.0, silent) is None  # пауза кончилась, но сразу после нее еще settle
    assert t.next(2.7, 0.0, silent) == "a\r"


def test_pause_after_a_line_drops_the_wait_for_reply_and_prompt():
    t = typist("a", Pause(1), "b", prompt=PROMPT)
    assert t.next(1.0, 0.1, lambda: ">> ") == "a\r"
    assert t.next(1.1, 0.0, lambda: ">> a") is None  # пауза началась
    assert t.next(2.2, 0.0, lambda: ">> a") is None  # кончилась, но settle не прошел
    assert t.next(3.0, 0.0, lambda: ">> a") == "b\r"  # ни ответа, ни приглашения ждать не стали


def test_pause_zero_is_a_noop():
    t = typist(Pause(0), "a", settle=0)
    assert t.next(0.0, 0.0, silent) == "a\r"


# --- момент снимка ---


def test_snapshot_after_counts_from_the_start():
    t = typist(snapshot=Snapshot(after=2), at=10.0)
    assert not t.pending
    assert t.watching
    assert not t.snapshot_due(11.9, 10.0, silent)
    assert t.snapshot_due(12.0, 10.0, silent)


def test_snapshot_without_a_condition_is_taken_at_once():
    assert typist(snapshot=Snapshot()).snapshot_due(0.0, 0.0, silent)


def test_snapshot_waits_for_the_script_and_counts_from_the_last_step():
    t = typist(Keys("a"), snapshot=Snapshot(after=1))
    assert not t.snapshot_due(100.0, 0.0, silent)  # шаги еще не выполнены
    assert t.next(5.0, 0.1, silent) == "a"
    assert not t.snapshot_due(5.9, 0.0, silent)
    assert t.snapshot_due(6.0, 0.0, silent)


def test_snapshot_when_looks_at_the_screen_text():
    t = typist(snapshot=Snapshot(when=r"Tasks:\s+\d+"))
    assert not t.snapshot_due(1.0, 1.0, lambda: "загрузка\r\n")
    assert t.snapshot_due(2.0, 2.0, lambda: "загрузка\r\nTasks: 42, 3 running\r\n")


def test_the_screen_is_read_for_the_snapshot_condition_only_after_new_output():
    screen = CountedScreen("ничего")
    t = typist(snapshot=Snapshot(when="готово"))
    assert not t.snapshot_due(1.0, 0.5, screen)
    assert not t.snapshot_due(1.1, 0.5, screen)  # вывода не прибавилось: экран заново не разбирается
    assert not t.snapshot_due(1.2, 1.15, screen)  # прибавилось: разбирается снова
    assert screen.reads == 2


def test_snapshot_when_then_after_counts_from_the_match():
    t = typist(snapshot=Snapshot(when="ok", after=2))
    assert not t.snapshot_due(1.0, 1.0, lambda: "нет")
    assert not t.snapshot_due(3.0, 3.0, lambda: "ok")  # совпало в момент 3.0
    assert not t.snapshot_due(4.9, 3.0, lambda: "ok")
    assert t.snapshot_due(5.0, 3.0, lambda: "ok")


def test_no_snapshot_means_never_due_and_nothing_to_watch_when_the_script_is_over():
    t = typist("a")
    assert t.watching
    assert t.next(1.0, 0.1, silent) == "a\r"
    assert not t.watching
    assert not t.snapshot_due(99.0, 0.0, silent)


@pytest.mark.parametrize(
    ("visible_only", "found"), [(False, True), (True, False)], ids=["whole history", "visible only"]
)
def test_snapshot_when_sees_scrolled_off_text_only_without_the_visible_only_flag(visible_only: bool, found: bool):
    output = "MARKER\r\n" + "filler\r\n" * 30  # метка ушла за верхний край экрана из 10 строк
    request = Request(
        argv=("x",),
        env={},
        rows=10,
        snapshot=Snapshot(when="MARKER"),
        capture_visible_only=visible_only,
    )
    assert Typist(request, started=0.0).snapshot_due(1.0, 1.0, lambda: output) is found
