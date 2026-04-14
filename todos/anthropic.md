# Anthropic wishlist

No API key yet — I drive Claude via **Claude Code** and **Cowork** (scheduled tasks,
remote triggers, plugins). These ideas assume that interface, not the raw SDK. If/when an
API key shows up, several of these become easier.

## Ideas

1. **Daily "what's in my head" briefing** — a scheduled Cowork task that reads my
   git activity, open PRs, and notes from the last 24h, and writes a 5-bullet morning
   briefing to a markdown file the website can render.
2. **Auto-generate /now page** — already a skill (`generate-now-page`). Wire it to fire
   on a schedule so the website /now page is always within 24h of fresh.
3. **Stale-TODO sweep** — Claude Code job that walks the repo weekly, finds TODOs older
   than 6 months, and either deletes them or opens an issue. Apply to every personal repo.
4. **PR pre-review** — on every PR I open in a personal repo, dispatch a Claude Code
   review pass that comments on the PR before I ask a human.
5. **Notebook-to-blog-post** — given a Jupyter notebook (this repo has one!), generate a
   draft blog post explaining what it does and what I learned.
6. **Emoji-summary upgrade** — the existing `/bsky/{handle}/emoji-summary` endpoint could
   call Claude (via Cowork as a worker) for a richer "vibe summary" of someone's posting.
7. **Personal-context skill** — build a skill that loads my memory dir + recent git
   activity + currently-playing Steam game, so any Claude session starts already knowing
   what I'm working on this week.

## Cross-service bonus

- **Anthropic × GitHub**: scheduled task that triages new issues across all my repos
  (label, prioritize, draft a reply) and posts a digest to a private gist.
- **Anthropic × Bluesky**: weekly task that drafts (not posts!) 3 candidate skeets based
  on my recent commits + recently played games + watch history. I pick which to post.
- **Anthropic × Discord**: see `discord.md` — a `!claude` command that dispatches Cowork.
- **Anthropic × Reddit**: morning briefing that summarizes the top of 3 chosen subs into
  a single page so I don't have to open Reddit at all.
- **Anthropic × YouTube**: given a video URL, fetch the transcript and produce a
  bullet-point summary on demand. Useful for "do I actually need to watch this?"
