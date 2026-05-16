# Features

Baseline of `coilysiren/backend`. Update when a headline feature changes.

## Purpose

FastAPI service behind `api.coilysiren.me`. Wraps the Bluesky AT Protocol with caching, social-graph analytics, and an emoji-summary NLP job. Ships as a container into the homelab k8s, OpenTelemetry to Honeycomb, errors to Sentry. Foundation for further personal-data integrations.

## HTTP API: Bluesky social analytics

- **Profile** - `GET /bsky/{handle}/profile` (cached profile + DID)
- **Followers / following** - paginated graph fetch (100/page)
- **Following handles only** - lightweight string-only variant
- **Mutuals** - intersection of followers and following
- **Follow popularity** - ranks who is most-followed by the handle's follow list
- **Suggested follows** - friends-of-friends recommendations
- **Author feed** - cursor-paginated post fetch, full or text-only

## NLP / data science

- **Emoji summary** - async job, polled for a ranked emoji vibe of recent posts
- **Keyword extraction** - YAKE-based scoring
- **NER + linguistic pipeline** - spaCy entity recognition aligned to emoji semantics
- **Stopword filtering** - NLTK pruning before scoring
- **Notebook surface** - emoji-summary algorithm exploration at `notebook.ipynb`

## Async tasks and caching

- **Background task dispatch** - fire-and-poll task ids stored in cache
- **Task status polling** - in_progress / completed / failed tri-state
- **Request cache** - 24h TTL, wraps Bluesky calls
- **Cache invalidation** - `POST /cache/clear/{suffix}`

## Observability

- **OpenTelemetry tracing** - FastAPI auto-instrumentation + custom cache spans
- **Honeycomb OTLP export** with bearer auth
- **Sentry** exception capture, prod-only DSN
- **Structured request logs** - structlog JSON middleware

## Platform and deployment

- **Container image** - Python 3.13 + uv multi-stage build, port 80
- **Kubernetes manifests** - Deployment, ClusterIP, Traefik Ingress, ExternalSecrets
- **Secret sync** - GHCR / Bluesky / Sentry creds from AWS SSM, 1h refresh
- **TLS** - cert-manager + Let's Encrypt via Traefik
- **Resource limits** - 100m/256Mi requests, 1 CPU / 512Mi limits
- **CORS / trusted hosts** - dev permissive, prod restricted to `coilysiren.me`
- **Rate limiting** - slowapi at 10 req/s per IP

## Auth and credentials

- **Bluesky atproto login** - app-password with 8h client refresh
- **Honeycomb API key** - env-injected OTLP bearer
- **Sentry DSN** - env-gated, no-op in dev

## CLI / dev tooling

- **Dev/debug CLI** - bsky XRPC invoker, feed text dump, emoji-summary runner, cache clear, streaming demo. Wrapped by Makefile + coily.
- **Toolchain** - ruff, mypy, pytest, ptipython, jupyter
- **Test endpoints** - `/explode` for forced exceptions, `/streaming` async generator demo

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

Cross-reference convention from [coilysiren/agentic-os-kai#313](https://github.com/coilysiren/agentic-os-kai/issues/313).
