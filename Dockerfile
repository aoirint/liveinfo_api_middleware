# syntax=docker/dockerfile:1.11
FROM python:3.12

ARG DEBIAN_FRONTEND=noninteractive
ARG PIP_NO_CACHE_DIR=1
ENV PYTHONUNBUFFERED=1
ENV PATH=/opt/liveinfo_api_middleware/.venv/bin:/home/user/.local/bin:${PATH}

RUN <<EOF
    set -eu

    apt-get update
    apt-get install -y \
        gosu

    apt-get clean
    rm -rf /var/lib/apt/lists/*
EOF

ARG CONTAINER_UID=2000
ARG CONTAINER_GID=2000
RUN <<EOF
    set -eu

    groupadd --non-unique --gid "${CONTAINER_GID}" user
    useradd --non-unique --uid "${CONTAINER_UID}" --gid "${CONTAINER_GID}" --create-home user
EOF

ARG POETRY_VERSION=1.7.1
RUN <<EOF
    set -eu

    gosu user pip install "poetry==${POETRY_VERSION}"

    gosu user poetry config virtualenvs.in-project true

    mkdir -p /home/user/.cache/pypoetry/{cache,artifacts}
    chown -R "user:user" /home/user/.cache
EOF

RUN <<EOF
    set -eu

    mkdir -p /opt/liveinfo_api_middleware
    chown -R user:user /opt/liveinfo_api_middleware
EOF

WORKDIR /opt/liveinfo_api_middleware
ADD --chown="${CONTAINER_UID}:${CONTAINER_GID}" ./pyproject.toml ./poetry.lock /opt/liveinfo_api_middleware/
RUN --mount=type=cache,uid="${CONTAINER_UID}",gid="${CONTAINER_GID}",target=/home/user/.cache/pypoetry/cache \
    --mount=type=cache,uid="${CONTAINER_UID}",gid="${CONTAINER_GID}",target=/home/user/.cache/pypoetry/artifacts <<EOF
    set -eu

    gosu user poetry install --no-root --only main
EOF

ADD --chown="${CONTAINER_UID}:${CONTAINER_GID}" ./liveinfo_api_middleware /opt/liveinfo_api_middleware/liveinfo_api_middleware
ADD --chown="${CONTAINER_UID}:${CONTAINER_GID}" ./README.md ./main.py /opt/liveinfo_api_middleware/
RUN --mount=type=cache,uid="${CONTAINER_UID}",gid="${CONTAINER_GID}",target=/home/user/.cache/pypoetry/cache \
    --mount=type=cache,uid="${CONTAINER_UID}",gid="${CONTAINER_GID}",target=/home/user/.cache/pypoetry/artifacts <<EOF
    set -eu

    gosu user poetry install --only main
EOF

CMD [ "gosu", "user", "poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000" ]
