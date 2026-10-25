"""
Создает во временном каталоге историю git с заранее известными именами и датами и печатает ее цветным графом.

Хеши коммитов зависят только от содержимого, автора, даты и сообщения, поэтому вывод одинаков на любой машине и не
зависит от истории самого проекта (в CI она обрезана, в контейнере ее нет). Настройки пользователя не читаются.
"""

import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

START = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

ISOLATED = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "author@example.com",
    "GIT_COMMITTER_NAME": "Test Author",
    "GIT_COMMITTER_EMAIL": "author@example.com",
    "GIT_PAGER": "cat",
}


def git(repo: str, minute: int, *arguments: str) -> None:
    when = (START + timedelta(minutes=minute)).isoformat()
    env = {**os.environ, **ISOLATED, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
    subprocess.run(["git", "-c", "init.defaultBranch=main", *arguments], cwd=repo, env=env, check=True, capture_output=True)


def build(repo: str) -> None:
    git(repo, 0, "init", "--quiet")
    git(repo, 1, "commit", "--allow-empty", "-m", "Start the project")
    git(repo, 2, "checkout", "--quiet", "-b", "feature")
    git(repo, 3, "commit", "--allow-empty", "-m", "Draw the picture")
    git(repo, 4, "checkout", "--quiet", "main")
    git(repo, 5, "commit", "--allow-empty", "-m", "Add the parser")
    git(repo, 6, "merge", "--no-ff", "--quiet", "-m", "Merge feature", "feature")
    git(repo, 7, "tag", "v1")


def main() -> int:
    with tempfile.TemporaryDirectory() as repo:
        build(repo)
        env = {**os.environ, **ISOLATED}
        sys.stdout.flush()
        return subprocess.run(
            ["git", "--no-pager", "log", "--oneline", "--graph", "--decorate", "--color=always"], cwd=repo, env=env
        ).returncode


if __name__ == "__main__":
    sys.exit(main())
