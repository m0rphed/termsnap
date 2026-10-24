"""
Единая точка входа для проверок проекта: то, что делает CI, а не конфигурация конкретного CI.

GitHub Actions, Docker, ``act`` и вы сами запускают одно и то же, поэтому от какого-то одного сервиса проект не
зависит: любой другой (Forgejo, GitLab, свой сервер) достаточно научить вызывать эту команду. Нужны только Python
(стандартная библиотека, 3.12 и новее) и ``uv``.

    python ci/run.py all                  # все проверки: стиль, типы, тесты
    python ci/run.py lint                 # ruff format --check и ruff check
    python ci/run.py types                # basedpyright
    python ci/run.py test -- -k pty -x    # pytest (все, что после --, уходит в pytest)
    python ci/run.py test --level unit    # только один уровень: unit, integration или external (см. tests/conftest.py)
    python ci/run.py --python 3.13 all    # другая версия Python, свое окружение .venv-ci-3.13
    python ci/run.py system-deps          # системные пакеты для Linux (шрифты, htop), для CI и Docker
    python ci/run.py docker 3.12 3.13 3.14     # то же в контейнерах: Linux на любой машине, где есть Docker или Podman
"""

import argparse
import io
import os
import platform
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: Версии Python, на которых проект проверяется по умолчанию.
PYTHONS = ("3.12", "3.13", "3.14")

#: Системные пакеты Debian и Ubuntu: шрифт с кириллицей для PNG и программы, которые снимаются в тестах.
APT_PACKAGES = ("fontconfig", "fonts-dejavu-core", "procps", "htop")

IMAGE = "termsnap-ci"

#: Уровни тестов (маркеры pytest, их ставит ``tests/conftest.py`` по каталогу): от быстрых к медленным.
LEVELS = ("unit", "integration", "external")


def run(command: Sequence[str], env: dict[str, str] | None = None) -> int:
    """
    Запускает команду в корне проекта, печатая ее, и возвращает код возврата.
    """
    print("$", " ".join(command), flush=True)
    try:
        return subprocess.run(command, cwd=ROOT, env=env).returncode
    except FileNotFoundError:
        print(f"не найдена программа {command[0]!r}", file=sys.stderr)
        return 127


def uv_env(python: str | None) -> dict[str, str]:
    """
    Окружение для uv. С ``python`` проверка идет в отдельном окружении ``.venv-ci-<версия>``, чтобы разные версии
    не перестраивали одно и то же ``.venv`` друг у друга.
    """
    env = dict(os.environ) | {"PYTHONUTF8": "1"}  # русский текст в логах CI, где вывод идет в канал и не в UTF-8
    if python is not None:
        env["UV_PYTHON"] = python
        env["UV_PROJECT_ENVIRONMENT"] = str(ROOT / f".venv-ci-{python}")
    return env


def sync(env: dict[str, str]) -> int:
    return run(["uv", "sync", "--locked"], env)


def lint(env: dict[str, str]) -> int:
    return max(run(["uv", "run", "ruff", "format", "--check"], env), run(["uv", "run", "ruff", "check"], env))


def types(env: dict[str, str]) -> int:
    return run(["uv", "run", "basedpyright"], env)


def test(env: dict[str, str], pytest_args: Sequence[str] = (), level: str | None = None) -> int:
    marker = ["-m", level] if level else []
    return run(["uv", "run", "pytest", "-ra", *marker, *pytest_args], env)


def system_deps() -> int:
    """
    Ставит системные пакеты (только Debian и Ubuntu; в Windows и macOS шрифты уже есть).
    """
    if sys.platform != "linux" or shutil.which("apt-get") is None:
        print("системные пакеты ставить не нужно (или это не Debian и Ubuntu): пропуск")
        return 0
    prefix = [] if os.geteuid() == 0 else ["sudo"] if shutil.which("sudo") else []
    code = run([*prefix, "apt-get", "update"])
    if code == 0:
        code = run([*prefix, "apt-get", "install", "-y", "--no-install-recommends", *APT_PACKAGES])
    return code


def docker(versions: Sequence[str], engine: str, *, no_cache: bool) -> int:
    """
    Собирает образ ``ci/Dockerfile`` для каждой версии Python и запускает в нем ``all``.
    """
    if shutil.which(engine) is None:
        print(f"нет {engine!r}: поставьте Docker или Podman (или укажите --engine)", file=sys.stderr)
        return 127
    results: dict[str, int] = {}
    for version in versions:
        tag = f"{IMAGE}:{version}"
        build = [engine, "build", "--build-arg", f"PYTHON={version}", "-t", tag, "-f", "ci/Dockerfile", "."]
        if no_cache:
            build.insert(2, "--no-cache")
        code = run(build)
        if code == 0:
            code = run([engine, "run", "--rm", tag])
        results[f"docker {version}"] = code
    return report(results)


def report(results: dict[str, int]) -> int:
    print("\n== итог ==")
    for name, code in results.items():
        print(f"  {'ok  ' if code == 0 else 'FAIL'} {name}")
    return 0 if all(code == 0 for code in results.values()) else 1


def check_all(python: str | None) -> int:
    env = uv_env(python)
    print(f"== {platform.platform()}, python {python or 'по умолчанию'}, {shutil.which('uv')} ==", flush=True)
    code = sync(env)
    if code != 0:
        return report({"sync": code})
    results: dict[str, int] = {}
    steps: list[tuple[str, Callable[[dict[str, str]], int]]] = [("lint", lint), ("types", types)]
    steps += [(f"test {level}", partial(test, level=level)) for level in LEVELS]
    for name, step in steps:
        started = time.monotonic()
        code = step(env)
        results[f"{name} ({time.monotonic() - started:.0f} с)"] = code
    return report(results)


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Проверки проекта: стиль, типы, тесты.")
    parser.add_argument("--python", help="версия Python (например, 3.13); по умолчанию та, что выберет uv")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("all", help="sync, lint, types, test: все проверки с итогом в конце")
    commands.add_parser("sync", help="uv sync --locked")
    commands.add_parser("lint", help="ruff format --check и ruff check")
    commands.add_parser("types", help="basedpyright")
    pytest_parser = commands.add_parser("test", help="pytest; аргументы после -- уходят в pytest")
    pytest_parser.add_argument("--level", choices=LEVELS, help="только один уровень тестов (по умолчанию все)")
    pytest_parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    commands.add_parser("system-deps", help="системные пакеты для Linux")
    docker_parser = commands.add_parser("docker", help="все проверки в контейнерах")
    docker_parser.add_argument("versions", nargs="*", default=list(PYTHONS), help="версии Python")
    docker_parser.add_argument(
        "--engine", default=os.environ.get("CONTAINER_ENGINE", "docker"), help="docker или podman"
    )
    docker_parser.add_argument("--no-cache", action="store_true", help="собрать образ заново")
    args = parser.parse_args(argv)

    env = uv_env(args.python)
    match args.command:
        case "all":
            return check_all(args.python)
        case "sync":
            return sync(env)
        case "lint":
            return lint(env)
        case "types":
            return types(env)
        case "test":
            pytest_args = [item for item in args.pytest_args if item != "--"]
            return test(env, pytest_args, args.level)
        case "system-deps":
            return system_deps()
        case "docker":
            return docker(args.versions, args.engine, no_cache=args.no_cache)
    return 2


if __name__ == "__main__":
    sys.exit(main())
