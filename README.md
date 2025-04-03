# backend

## Global Installs

```bash
brew install pyenv
brew install poetry
brew install curl
brew install jq
brew install redis

poetry config virtualenvs.in-project true
poetry sync
poetry self add poetry-plugin-export
poetry export -f requirements.txt --output requirements.txt --without-hashes
pip install -r requirements.txt
```

## Local Development

Create .env file with the following contents

```bash
BSKY_USERNAME=coilysiren.me # use yours, not mine
BSKY_PASSWORD=1244-1244-1244-1244 # this is a placeholder, create a real one here: https://bsky.app/settings/app-passwords

BSKY_BOT_USERNAME=coilysiren-bot.bsky.social
BSYK_BOT_PASSWORD=1244-1244-1244-1244

OTEL_SDK_DISABLED=true
REDISCLOUD_URL=redis://default:@127.0.0.1:6379 # Would be nice if heroku just provisioned it as "REDIS_URL", but alas. And we should match heroku locally.
```

Initialize the virtualenv like so

```bash
poetry sync
```

In one terminal, run this:

```bash
poetry run uvicorn src.main:app --reload --port 4000 --host 0.0.0.0
```

In a second terminal, run this:

```bash
curl "http://localhost:4000/bsky/coilysiren.me/profile" | jq # again, use your handle, not mine
```

In a yet 3rd terminal, try this:

```bash
invoke bsky --path app.bsky.feed.getTimeline --kwargs ""
```

### Data Processing

```bash
poetry run jupyter notebook
```
