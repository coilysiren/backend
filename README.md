# backend

## Global Installs

https://brew.sh/

https://www.rust-lang.org/

```bash
brew install pyenv
brew install curl
brew install jq
brew install redis

# https://github.com/chmln/sd
cargo install sd

pip install poetry
poetry config virtualenvs.in-project true
poetry sync
poetry self add poetry-plugin-export
poetry export -f requirements.txt --output requirements.txt --without-hashes

# Optional:
# pip install -r requirements.txt
```

## Local Development

### The basics

Create .env file with the following contents

```bash
BSKY_USERNAME=coilysiren.me # use yours, not mine
BSKY_PASSWORD=1244-1244-1244-1244 # this is a placeholder, create a real one here: https://bsky.app/settings/app-passwords

BSKY_BOT_USERNAME=coilysiren-bot.bsky.social
BSYK_BOT_PASSWORD=1244-1244-1244-1244

OTEL_SDK_DISABLED=true
REDISCLOUD_URL=redis://default:@127.0.0.1:6379 # Would be nice if heroku just provisioned it as "REDIS_URL", but alas. And we should match heroku locally.
```

### Build

Native

```bash
poetry sync
```

Container

```bash
docker build \
  -t coilysiren/backend:$(git rev-parse --short HEAD) \
  -t coilysiren/backend:latest \
  .
```

```powershell
docker build `
  -t coilysiren/backend:$(git rev-parse --short HEAD) `
  -t coilysiren/backend:latest `
  .
```

### API developement

In one terminal, run either of these

```bash
poetry run uvicorn src.main:app --reload --port 4000 --host 0.0.0.0
docker run --name coilysiren/backend --rm coilysiren/backend
```

In a second terminal, run this:

```bash
curl "http://localhost:4000/bsky/coilysiren.me/profile" | jq
```

### Data Science

```bash
poetry run jupyter notebook
```
