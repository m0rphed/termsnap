"""
Крошечный REPL для проверок ввода: команды ``add a b``, ``slow`` (молчит полторы секунды), ``fail`` и ``exit``.

Приглашение печатается отдельно от ``input()``, чтобы работало одинаково везде (без readline).
"""

import sys
import time

PROMPT = "\x1b[1;32m>>\x1b[0m "

print("\x1b[2mmini-repl: add a b | slow | fail | exit\x1b[0m")
while True:
    print(PROMPT, end="", flush=True)
    try:
        line = input()
    except EOFError:
        break
    if not line.strip():
        continue
    command, *arguments = line.split()
    if command == "add":
        print(f"\x1b[36m{sum(int(item) for item in arguments)}\x1b[0m")
    elif command == "slow":
        time.sleep(1.5)
        print("медленно, но готово")
    elif command == "fail":
        print("\x1b[31mошибка: команда не удалась\x1b[0m", file=sys.stderr)
    elif command == "exit":
        print("пока")
        break
    else:
        print(f"\x1b[31mнеизвестная команда: {command}\x1b[0m")
