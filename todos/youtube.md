# YouTube wishlist

Credentials: Google OAuth flow already wired in `../website/scripts/youtube-auth.js`,
token cached at `.youtube-token.json`.

## Ideas

1. **Watch-history mood ring** — pull recently watched videos, group by channel/topic,
   expose an endpoint that says "this week I've been on a {topic} kick".
2. **Liked-video archive** — every liked video gets snapshotted (title, channel, url,
   thumbnail) into Redis/S3 so I have a permanent record even if the video gets deleted.
3. **Subscription firehose** — endpoint that returns the latest upload from every channel
   I'm subscribed to, sorted by recency. A personal YouTube "inbox".
4. **Channel-level stats for my own channel** — view counts, subs over time, top videos
   this month. Cache and expose as JSON for the website.
5. **"Currently watching" badge** — set a most-recent-video field on the website /now
   page automatically.
6. **Playlist auto-curator** — endpoint that takes a search query and returns videos from
   only channels I'm already subscribed to. A trusted-source filter.
7. **Comment archive** — pull every comment I've ever left on YouTube into a searchable
   table. Good for "wait, what was that channel I commented on last year?"

## Cross-service bonus

- **YouTube × Bluesky**: auto-skeet when I publish a new video on my channel, with the
  thumbnail and a one-line description.
- **YouTube × Reddit**: when I upload a video, scan related subreddits for active threads
  on the topic and surface them to me (don't auto-post — just surface).
- **YouTube × Discord**: a `!latest` command in my Discord that returns my most-recent
  liked video. Shareable taste-of-the-day.
- **YouTube × GitHub**: cross-link videos and code repos by topic, generating a
  "see-also" section on each repo's README.
