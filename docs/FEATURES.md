# Features

Baseline inventory of what `coilysiren/backend` does today. Use this to evaluate scope increases or decreases over time. Update when a headline feature is added, removed, or meaningfully reshaped.

## Purpose

FastAPI service behind `api.coilysiren.me`. Wraps the Bluesky AT Protocol with caching, social-graph analytics, and an emoji-summary NLP job. Ships as a container into a Kubernetes homelab with OpenTelemetry to Honeycomb and errors to Sentry. Designed as a foundation for further personal-data integrations (GitHub, YouTube, Reddit, Steam, Discord, LLM APIs).

## HTTP API: Bluesky social analytics

- **Profile** - `GET /bsky/{handle}/profile` - profile + DID lookup with caching - [backend/main.py:86](backend/main.py:86), [backend/bsky.py:146](backend/bsky.py:146)
- **Followers / following** - `GET /bsky/{handle}/followers`, `/following` - paginated graph fetch (100/page) - [backend/main.py:56](backend/main.py:56), [backend/bsky.py:155](backend/bsky.py:155)
- **Following handles only** - `GET /bsky/{handle}/following/handles` - lightweight string-only variant - [backend/main.py:74](backend/main.py:74), [backend/bsky.py:173](backend/bsky.py:173)
- **Mutuals** - `GET /bsky/{handle}/mutuals` - intersection of followers and following - [backend/main.py:92](backend/main.py:92)
- **Follow popularity** - `GET /bsky/{handle}/popularity[/{index}]` - ranks who is most-followed by the handle's follow list - [backend/main.py:104](backend/main.py:104), [backend/bsky.py:59](backend/bsky.py:59)
- **Suggested follows** - `GET /bsky/{handle}/suggestions[/{index}]` - friends-of-friends recommendations - [backend/main.py:137](backend/main.py:137), [backend/bsky.py:92](backend/bsky.py:92)
- **Author feed** - `GET /bsky/{handle}/feed`, `/feed/text` - cursor-paginated post fetch, full or text-only - [backend/main.py:171](backend/main.py:171), [backend/bsky.py:182](backend/bsky.py:182)

## NLP / data science

- **Emoji summary** - async job at `POST /bsky/{handle}/emoji-summary` returning a task id, polled for a ranked emoji vibe of recent posts - [backend/main.py:205](backend/main.py:205), [backend/worker.py:6](backend/worker.py:6)
- **Keyword extraction** - YAKE-based keyword scoring of post text - [backend/data_science.py](backend/data_science.py)
- **NER + linguistic pipeline** - spaCy entity recognition aligned to emoji semantics - [backend/data_science.py](backend/data_science.py)
- **Stopword filtering** - NLTK stopword pruning before scoring - [backend/data_science.py](backend/data_science.py)
- **Notebook surface** - exploration of the emoji-summary algorithm - [notebook.ipynb](notebook.ipynb)

## Async tasks and caching

- **Background task dispatch** - fire-and-poll task ids stored in cache - [backend/worker.py](backend/worker.py), [backend/cache.py:38](backend/cache.py:38)
- **Task status polling** - in_progress / completed / failed tri-state via cache - [backend/cache.py:38](backend/cache.py:38)
- **Request cache** - 24h TTL keyed by prefix + suffix, wraps Bluesky calls - [backend/cache.py:72](backend/cache.py:72)
- **Cache invalidation** - `POST /cache/clear/{suffix}` deletes matching keys - [backend/main.py:34](backend/main.py:34)

## Observability

- **OpenTelemetry tracing** - FastAPI auto-instrumentation plus custom cache spans - [backend/telemetry.py](backend/telemetry.py), [backend/application.py:24](backend/application.py:24)
- **Honeycomb OTLP export** - bearer-auth OTLP traces - [backend/telemetry.py:31](backend/telemetry.py:31)
- **Sentry** - exception capture with FastAPI + Starlette integrations, prod-only DSN - [backend/telemetry.py:46](backend/telemetry.py:46)
- **Structured request logs** - structlog JSON middleware logging method, path, query, status - [backend/application.py:24](backend/application.py:24)

## Platform and deployment

- **Container image** - Python 3.13 + uv multi-stage build, port 80 - [Dockerfile](Dockerfile)
- **Kubernetes manifests** - Deployment, ClusterIP Service, Traefik Ingress, ExternalSecrets - [deploy/main.yml](deploy/main.yml)
- **Secret sync** - GHCR pull creds, Bluesky creds, Sentry DSN sourced from AWS SSM Parameter Store on 1h refresh - [deploy/main.yml:11](deploy/main.yml:11)
- **TLS** - cert-manager + Let's Encrypt via Traefik - [deploy/main.yml:154](deploy/main.yml:154)
- **Resource limits** - 100m/256Mi requests, 1 CPU / 512Mi limits - [deploy/main.yml:99](deploy/main.yml:99)
- **CORS / trusted hosts** - dev permissive, prod restricted to `coilysiren.me`, `api.coilysiren.me` - [backend/application.py:147](backend/application.py:147)
- **Rate limiting** - slowapi at 10 req/s per IP on most routes - [backend/application.py:175](backend/application.py:175)

## Auth and credentials

- **Bluesky atproto login** - app-password login with 8h client refresh - [backend/bsky.py:26](backend/bsky.py:26)
- **Honeycomb API key** - env-injected OTLP bearer - [backend/telemetry.py:36](backend/telemetry.py:36)
- **Sentry DSN** - env-gated, no-op in dev - [backend/telemetry.py:46](backend/telemetry.py:46)

## CLI / dev tooling

- **Dev/debug CLI** - bsky XRPC invoker, author-feed text dump, emoji-summary runner, cache clear, video stream demo. Argparse subcommands wrapped by Makefile + coily - [backend/cli.py](backend/cli.py)
- **Makefile** - `build-native`, `build-docker`, `run-native` (uvicorn :4000), `run-docker`, `deploy`, plus per-CLI-subcommand targets - [Makefile](Makefile)
- **Toolchain** - ruff, mypy, pytest, ptipython, jupyter - [pyproject.toml](pyproject.toml)
- **Test endpoints** - `/explode` for forced exceptions, `/streaming` async generator demo - [backend/main.py:28](backend/main.py:28), [backend/streaming.py](backend/streaming.py)

## Planned integrations (not yet implemented)

Listed in [backend/main.py:238](backend/main.py:238) as backlog. Track scope creep against this set.

- GitHub (commit heatmaps, PR/issue summaries)
- YouTube Data API (OAuth, uploads, watch history)
- Reddit public API (recent posts/comments)
- Steam Web API (recently played, achievements)
- Discord bot or webhook surface
- Anthropic Claude (summarization, vibe refinement)
- OpenAI (fallback embeddings/completions)
- AWS boto3 (SSM, S3 artifact cache)
- Netlify webhooks (rebuild trigger on data change)

## See also

- [README.md](../README.md) - human-facing intro.
- [AGENTS.md](../AGENTS.md) - agent-facing operating rules.
- [.coily/coily.yaml](../.coily/coily.yaml) - allowlisted commands.

Cross-reference convention from [coilysiren/coilyco-ai#313](https://github.com/coilysiren/coilyco-ai/issues/313).
