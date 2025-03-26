web: opentelemetry-instrument \
  --traces_exporter console \
  --metrics_exporter console \
  --logs_exporter console \
    uvicorn src.main:app --host=0.0.0.0 --port $PORT
