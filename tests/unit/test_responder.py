"""
Ответы терминала на запросы программы (позиция курсора, тип терминала, состояние): без них программа зависает.
"""

from helpers import ESC
from support import require_module

require_module("pyte")

from termsnap.screen import Responder


def answer(data: bytes) -> bytes:
    return Responder(80, 24).feed(data)


def test_cursor_position_is_reported_after_the_text_printed_so_far():
    assert answer(f"abc{ESC}[6n".encode()) == f"{ESC}[1;4R".encode()


def test_cursor_position_follows_the_cursor_moves():
    assert answer(f"{ESC}[3;5H{ESC}[6n".encode()) == f"{ESC}[3;5R".encode()


def test_device_attributes_are_answered_as_a_vt102():
    assert answer(f"{ESC}[c".encode()) == f"{ESC}[?6c".encode()


def test_status_request_is_answered_as_all_right():
    assert answer(f"{ESC}[5n".encode()) == f"{ESC}[0n".encode()


def test_ordinary_output_gets_no_answer():
    assert answer(f"hello {ESC}[1;31mred{ESC}[0m".encode()) == b""


def test_characters_and_requests_split_between_chunks_are_still_understood():
    data = f"привет{ESC}[6n".encode()
    responder = Responder(80, 24)
    assert responder.feed(data[:3]) == b""  # оборвано посреди буквы
    assert responder.feed(data[3:-2]) == b""  # и посреди запроса
    assert responder.feed(data[-2:]) == f"{ESC}[1;7R".encode()


def test_an_old_request_is_not_answered_again():
    responder = Responder(80, 24)
    assert responder.feed(f"{ESC}[6n".encode())
    assert responder.feed(b"more") == b""
