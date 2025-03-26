# backend

## Global Installs

```bash
brew install poetry
brew install curl
brew install jq
```

## Local Development

Create .env file with the following contents

```bash
BSKY_PASSWORD=1234-1234-1234-1234 # this is a placeholder, create a real one here: https://bsky.app/settings/app-passwords
BSKY_USERNAME=coilysiren.me # use yours, not mine
```

In one terminal, run this:

```bash
poetry run uvicorn src.main:app --reload --port 3000 --host 0.0.0.0
```

In a second terminal, run this:

```bash
curl "http://localhost:3000/bksy/following/?handle=coilysiren.me" | jq # again, use your handle, not mine
```
