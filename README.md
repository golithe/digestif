![CI](https://github.com/golithe/digestif/actions/workflows/ci.yml/badge.svg)

# digestif

A gloriously over-engineered daily newsletter digest — built to self-host on a Raspberry Pi or any
always-on machine.

It fetches top stories from [Hacker News](https://news.ycombinator.com) and
[Lobste.rs](https://lobste.rs), scrapes the linked articles, runs them through a free tier [Mistral](https://console.mistral.ai/)
LLM to produce a short summary, formats everything into a styled HTML email and sends it via
[Resend](https://resend.com).

Yes, this is massive overkill. This is why I added Github Actions for CI and renovateBot to keep
dependencies up to date.

## What it does

1. Fetches top stories from HN and Lobsters (async, naturally)
1. Scrapes and truncates the linked article text
1. Generates AI summaries via the Mistral API
1. Formats a styled HTML newsletter
1. Emails it to you — twice a day via cron

## Deployment

This project is designed to run in Docker. The container includes a cron job that fires at 07:00
and 16:00 every day. Running `src/main.py` directly with `uv run` won't work — the required
environment variables won't be set.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with the Compose plugin
- A `.env` file in the project root (see Configuration below)

### Building and Running

```
docker compose build
docker compose up -d
docker compose exec app python /app/src/main.py
```

That's it. The container handles everything else.

### Watching for changes (dev mode)

```
docker compose watch
```

This syncs local changes into the container and rebuilds when `uv.lock` changes.

## Configuration

Create a `.env` file in the project root:

```
MISTRAL_API_KEY=...
RESEND_API_KEY=...
RESEND_FROM=digest@yourdomain.com
NL_RECIPIENT=you@example.com
SELECTION_MODE=top
TAG=latest
```

| Variable | Description |
| --- | --- |
| `MISTRAL_API_KEY` | Your [Mistral](https://console.mistral.ai) API key |
| `RESEND_API_KEY` | Your [Resend](https://resend.com) API key |
| `RESEND_FROM` | Sender address (must be a verified domain in Resend) |
| `NL_RECIPIENT` | Recipient email address |
| `SELECTION_MODE` | `top` (default) or `random` |
| `TAG` | Docker image tag to use (e.g. `latest`) |

## Local tooling

The only things that work locally without Docker are the dev tooling commands. These require
[uv](https://docs.astral.sh/uv/getting-started/installation/) to be installed.

### Formatting and linting

```
uv run ruff format
uv run ruff check --fix
```

### Tests

```
uv run pytest
```
