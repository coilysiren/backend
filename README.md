# backend

FastAPI service behind api.coilysiren.me. Deploys to the k3s homelab via the canonical rig in [infrastructure/docs/k3s-deploy-notes.md](../infrastructure/docs/k3s-deploy-notes.md).

## Install

```bash
brew install uv jq ffmpeg mpv
brew install --cask docker
```

## Environment

Create `.env`:

```bash
BSKY_USERNAME=coilysiren.me
BSKY_PASSWORD=xxxx-xxxx-xxxx-xxxx   # https://bsky.app/settings/app-passwords
BSKY_BOT_USERNAME=coilysiren-bot.bsky.social
BSKY_BOT_PASSWORD=xxxx-xxxx-xxxx-xxxx
OTEL_SDK_DISABLED=true
```

## Run

```bash
make build-native    # uv sync + export requirements.txt
make run-native      # uvicorn on :4000

make build-docker
make run-docker

curl http://localhost:4000/bsky/coilysiren.me/profile | jq
```

## Data science notebook

```bash
uv run jupyter notebook
```

## Commands

Dev commands are declared in [`.coily/coily.yaml`](.coily/coily.yaml). Run them as `coily exec <verb>`.
