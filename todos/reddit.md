# Reddit wishlist

Credentials: public API, no auth needed (see `../website/fetch-now-data.js`). Optional:
add a script-app client_id/secret to lift rate limits and access my own user data.

## Ideas

1. **My-comment archive** — full export of every comment I've ever made, with parent
   post context, into a searchable JSON dump. Reddit can and does delete things.
2. **Saved-post inbox** — endpoint that lists my Reddit "saved" items, normalized so I
   can build a personal read-later UI.
3. **Subreddit "today's best"** — for a curated list of subs, return the top post of the
   day, deduped against what I've already seen this week.
4. **Trend tracker** — track word frequency in r/{subreddit}/new over time so I can spot
   memes/topics rising before they hit r/all.
5. **Karma graph** — daily snapshot of my comment + post karma, expose as a sparkline.
6. **Niche-sub discovery** — given a sub I like, find smaller subs that share a high
   percentage of top commenters with it.
7. **Thread-of-doom watcher** — given a thread URL, track its comment count and top
   comment over time. Useful for AMAs and breaking-news megathreads.

## Cross-service bonus

- **Reddit × Bluesky**: when a Bluesky post of mine gets shared to a subreddit, surface
  the discussion link back into my notifications.
- **Reddit × Anthropic (Claude Code)**: have Claude Code summarize the top of r/{sub}
  every morning into a 5-bullet briefing — like a personal Morning Brew.
- **Reddit × YouTube**: when a Reddit thread links to my YouTube video, snapshot the
  thread context so I have a record of who shared it and why.
- **Reddit × GitHub**: scan programming subs for mentions of any of my repo names and
  open a GitHub issue tagged `mentioned-on-reddit` with the link.
