# backend

## Global Installs

```bash
brew install pyenv
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

## Testing Telemetry

```bash
# bash
poetry run opentelemetry-instrument \
  --exporter_otlp_endpoint "https://api.honeycomb.io" \
  --exporter_otlp_headers "$OTEL_EXPORTER_OTLP_HEADERS" \
  --exporter_otlp_protocol "http/protobuf" \
  --service_name "backend" \
  uvicorn src.main:app --host 0.0.0.0 --port 3000
```

```bash
# powershell
poetry run opentelemetry-instrument `
  --exporter_otlp_endpoint "https://api.honeycomb.io" `
  --exporter_otlp_headers "$env:OTEL_EXPORTER_OTLP_HEADERS" `
  --exporter_otlp_protocol "http/protobuf" `
  --service_name "backend" `
  uvicorn src.main:app --host 0.0.0.0 --port 3000
```
