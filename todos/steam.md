# Steam wishlist

Credentials: Steam Web API key in `../website/.steam-credentials.json`.
Likely env var: `STEAM_API_KEY`, plus my SteamID64.

## Ideas

1. **Hours-played leaderboard** — endpoint returning my top 20 most-played games of all
   time, plus the delta over the last 30 days. Surfaces what I'm actually playing now.
2. **"Currently playing" /now feed** — most recently played game (within last 2 weeks),
   with cover art and total hours. Drop straight into the website /now page.
3. **Achievement tracker** — for a chosen game, return remaining achievements sorted by
   global rarity. Personal completionist dashboard.
4. **Backlog shamer** — list of games I own but have <30 minutes on. Optional weekly
   email or Bluesky skeet of "you should try X this weekend".
5. **Wishlist price-watch** — snapshot wishlist prices daily, alert me when something
   drops more than X%. (Wishlist is on the public profile, no auth needed.)
6. **Friends-overlap finder** — given a game I want to play, list which Steam friends
   own it, sorted by recent activity. "Who can I play this with tonight?"
7. **Genre-fingerprint** — aggregate the tags on every game I own, output a top-10 of my
   actual taste vs. what I claim my taste is.

## Cross-service bonus

- **Steam × Bluesky**: weekly auto-skeet of "this week I played: X (Y hours), Z (W
  hours)". Lightweight gaming activity log.
- **Steam × Discord**: Discord bot command `!playing` that returns what I'm currently in
  the middle of so friends can join. Show backlog suggestions in a `#what-to-play` channel.
- **Steam × YouTube**: when I start playing a new game, surface the top "tips for
  beginners" video from a trusted-channel allowlist.
- **Steam × Reddit**: pull the top thread from r/{game-subreddit} for the game I most
  recently played, daily.
