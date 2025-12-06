# syntax=docker/dockerfile:1
ARG BASE_IMAGE=ubuntu:24.04
ARG PYTHON_VERSION=3.12
ARG UV_VERSION=0.9

# Download uv binary stage
FROM "ghcr.io/astral-sh/uv:${UV_VERSION}" AS uv-reference

# Build uv and Python base stage
FROM "${BASE_IMAGE}" AS uv-python-base

ARG DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

ENV PYTHONUNBUFFERED=1

ARG UV_VERSION
COPY --from=uv-reference /uv /uvx /bin/

ENV UV_PYTHON_CACHE_DIR="/uv_python_cache"
ENV UV_PYTHON_INSTALL_DIR="/opt/python"
ENV PATH="${UV_PYTHON_INSTALL_DIR}/bin:${PATH}"

ARG PYTHON_VERSION
RUN --mount=type=cache,target=/uv_python_cache <<EOF
    uv python install "${PYTHON_VERSION}"
EOF


# Build Python virtual environment stage
FROM uv-python-base AS build-venv

#  uv configuration
# - Generate bytecodes
# - Copy packages into virtual environment
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install Python dependencies
COPY ./pyproject.toml uv.lock /opt/liveinfo_api_middleware/
RUN --mount=type=cache,target=/root/.cache/uv <<EOF
    cd /opt/liveinfo_api_middleware

    UV_PROJECT_ENVIRONMENT="/opt/python_venv" uv sync --locked --no-dev --no-editable --no-install-project
EOF


# Runtime stage
FROM uv-python-base AS runtime

# Install OS dependencies
# - tzdata: time zone data
RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt/lists <<EOF
    apt-get update

    apt-get install -y --no-install-recommends \
        tzdata
EOF

# Copy Python virtual environment from build stage
COPY --from=build-venv /opt/python_venv /opt/python_venv
ENV PATH="/opt/python_venv/bin:${PATH}"

# Copy application files
COPY ./liveinfo_api_middleware /opt/liveinfo_api_middleware/liveinfo_api_middleware

# Pre-compile Python bytecode
RUN <<EOF
    cd /opt/liveinfo_api_middleware

    python -m compileall ./liveinfo_api_middleware
EOF

USER "2000:2000"

CMD [ "fastapi", "run", "/opt/liveinfo_api_middleware/liveinfo_api_middleware" ]
