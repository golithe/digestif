FROM python:3.15.1-slim-trixie@sha256:533b0b2f9b5d46fd097091cf826f27902f1d6c3bca714b6dc74551356aa97a51 AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 /uv /usr/local/bin/uv

WORKDIR /app

# The venv must link against the runtime stage's interpreter, so never fetch a uv-managed one.
ENV UV_PYTHON_DOWNLOADS=0 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project


FROM python:3.15.1-slim-trixie@sha256:533b0b2f9b5d46fd097091cf826f27902f1d6c3bca714b6dc74551356aa97a51

RUN apt-get update && apt-get install -y --no-install-recommends cron && rm -rf /var/lib/apt/lists/*

RUN echo "00 7,16 * * * root /bin/bash /app/run_script.sh > /proc/1/fd/1 2>&1" > /etc/cron.d/mycron \
    && chmod 0644 /etc/cron.d/mycron

WORKDIR /app

# Dependencies and code are separate layers so a code-only release re-pulls only a few KB.
COPY --from=builder /app/.venv /app/.venv
COPY run_script.sh /app/run_script.sh
COPY src /app/src

ENV PATH="/app/.venv/bin:$PATH"

# Cron jobs start with an empty environment, so the container's is saved for run_script.sh.
# export -p quotes values; plain `env` output breaks on spaces or <> when sourced.
CMD ["bash", "-c", "export -p > /etc/environment && chmod 600 /etc/environment && exec cron -f"]
