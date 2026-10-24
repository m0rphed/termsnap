# Linux-проверки в контейнере: те же команды, что в CI, но на любой машине с Docker или Podman.
#
#   python ci/run.py docker 3.13 3.14
#
# Собирать нужно из корня проекта (контекст сборки - весь проект).
# syntax=docker/dockerfile:1
ARG PYTHON=3.14
FROM ghcr.io/astral-sh/uv:python${PYTHON}-bookworm-slim
ARG PYTHON  # ARG до FROM после него не виден, поэтому объявляется заново

# Системные пакеты берутся из того же скрипта, что и в CI. Node.js нужен примерам с node; git нарочно не ставится:
# в образе нет истории, и пример с git log не имеет смысла (тест пропускается, если git нет).
COPY ci/run.py /tmp/ci/run.py
RUN python /tmp/ci/run.py system-deps && apt-get install -y --no-install-recommends nodejs ca-certificates \
    && rm -rf /var/lib/apt/lists/* /tmp/ci

# Окружение вне каталога проекта, интерпретатор берется системный, а не скачивается.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_PYTHON=${PYTHON} \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUTF8=1

WORKDIR /work

# Сначала зависимости: этот слой не пересобирается, пока не менялись pyproject.toml и uv.lock.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

COPY . .
RUN uv sync --locked

CMD ["python", "ci/run.py", "all"]
