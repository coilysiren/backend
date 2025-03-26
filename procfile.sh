#! /usr/bin/env bash

set -eux

opentelemetry-instrument \
  --exporter_otlp_endpoint "https://api.honeycomb.io" \
  --exporter_otlp_headers "$OTEL_EXPORTER_OTLP_HEADERS" \
  --exporter_otlp_protocol "http/protobuf" \
  --service_name "backend" \
  uvicorn src.main:app --host=0.0.0.0 --port "$PORT"
