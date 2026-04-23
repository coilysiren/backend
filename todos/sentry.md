# Sentry status page

Powers a public `/status` route on coilysiren.me. Backend pulls Sentry's API,
frontend renders. This file is the plan; implement in slices.

Credentials: scoped read-only auth token in AWS SSM at `/sentry/readonly-token`.
Add to the SSM inventory in `../AGENTS.md` when the token is created. Token
scopes: `event:read`, `project:read`, `org:read`. Nothing more.

Org slug and project slugs are not secret; hardcode or surface via env
(`SENTRY_ORG`, `SENTRY_PROJECTS`). Default base URL `https://sentry.io/api/0/`.

## Why this exists

Sentry has no first-class public dashboard. Everything in-product is auth-gated.
The goal is a public, read-only "how's the homelab" surface that makes the
observability work visible without handing out org access.

Secondary goal: the repo itself is part of the observability-backfill story
against my resume. Ship it, write it up, cross-link from the website.

## Backend (this repo)

New module: `src/sentry.py`. FastAPI router mounted under `/sentry`.

1. **`GET /sentry/summary`** - rollup for the full org. Returns:
   - total events last 24h / 7d / 30d
   - unresolved issue count (org-wide)
   - latest release name + age
   - crash-free session rate if sessions are enabled, else null
2. **`GET /sentry/projects`** - per-project breakdown. For each project in
   `SENTRY_PROJECTS`: name, event count 7d, unresolved count, last seen event
   timestamp. Powers the "services" table on the frontend.
3. **`GET /sentry/issues/top`** - top N unresolved issues by event count, last
   7d. Title, culprit, event count, first seen, last seen, permalink. N=10
   default, cap at 25.
4. **`GET /sentry/releases/recent`** - last 5 releases across the org. Version,
   date created, project count, new issue count. Lets the frontend show "what
   shipped recently and did it break anything."

All responses JSON. All cached in Redis (already available, see `src/cache.py`)
with a 5-10 minute TTL. Sentry's rate limits are generous but a HN hug would
still blow through them.

## Safety before shipping

Sentry returns more than a public page should show. Strip or allowlist on the
backend, not the frontend, so a leak would require a backend change (auditable
in git).

- **Strip**: stack trace frames, request bodies, breadcrumbs, user context, IP,
  env vars, server names, file paths.
- **Keep**: issue title, culprit (usually just the function name), event count,
  first/last seen, permalink (`https://sentry.io/...` - fine to expose, it's
  auth-gated on Sentry's side).
- **Consider**: truncate issue titles to N chars in case they embed prod data.
- **Deny-list**: hardcode a list of project slugs that are never exposed, as a
  backstop in case `SENTRY_PROJECTS` ever gets misconfigured.

## Frontend (website repo)

New route: `src/pages/status.astro` (or `.tsx`, match existing convention).
Server-rendered at request time, hits the backend's `/sentry/*` endpoints,
caches the HTML at the edge for 5 min.

Layout roughly:

- Top: green/yellow/red status pill driven by "any critical unresolved issues
  in last 24h?"
- Section 1: summary tiles (events 24h/7d/30d, unresolved count, last release).
- Section 2: per-service table (from `/sentry/projects`).
- Section 3: top issues (from `/sentry/issues/top`), linked to Sentry.
- Section 4: recent releases (from `/sentry/releases/recent`).
- Footer: "data from Sentry, updated every N minutes, see repo on GitHub."

Mobile-first. The point of rolling this over a Grafana public dashboard is that
it actually reads well on a phone.

## Sequencing

1. Wire Sentry SDK into the backend, website build, and one other service
   (eco-mcp-app is the easy pick) so there's real data to query. Without this,
   the status page is empty and the whole thing is vapor.
2. Create the scoped SSM token, add to AGENTS.md inventory.
3. Ship backend `/sentry/summary` first. One endpoint, one test, deploy.
4. Add `/sentry/projects`, then `/sentry/issues/top`, then `/releases/recent`.
5. Frontend `/status` page consuming `/sentry/summary`. Iterate.
6. Write it up on coilysiren.me. Cross-post.

## Open questions

- Use Sentry's Sessions product for crash-free rate, or skip? Sessions need
  SDK-side opt-in and cost event volume. Decide after step 1 shows what volume
  looks like.
- Public dashboard on Grafana Cloud as a secondary surface for the "real"
  metrics (CPU, memory, pod restarts) when Alloy lands? Probably yes, but link
  to it from /status rather than embed.
- Should the status page show historical trends (events/day sparkline for 30d)?
  Nice to have; not v1. Sentry's `stats_v2` endpoint supports it cheaply.

## Cross-service bonus

- **Sentry x Discord**: when unresolved count crosses a threshold, post to the
  `bots` channel. Low-noise replacement for email alerts.
- **Sentry x Bluesky**: weekly auto-skeet "homelab shipped N releases, caught M
  errors, here's what broke." Makes the o11y work legible as content.
- **Sentry x claude-code-pulse**: surface unresolved-issue count in the
  statusline when working in any coilysiren repo. Ambient awareness.
