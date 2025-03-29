import os

import dotenv
import opentelemetry.exporter.otlp.proto.http.metric_exporter as otel_metric_exporter
import opentelemetry.exporter.otlp.proto.http.trace_exporter as otel_trace_exporter
import opentelemetry.metrics as otel_metrics
import opentelemetry.sdk.metrics as otel_sdk_metrics
import opentelemetry.sdk.metrics.export as otel_metrics_export
import opentelemetry.sdk.resources as otel_resources
import opentelemetry.sdk.trace as otel_sdk_trace
import opentelemetry.sdk.trace.export as otel_export
import opentelemetry.trace as otel_trace
import sentry_sdk


dotenv.load_dotenv()


class Telemetry(object):
    # https://opentelemetry.io/docs/languages/python/instrumentation/

    initalized = False
    tracer: otel_trace.Tracer = None
    meter: otel_metrics.Meter = None
    resource: otel_resources.Resource = otel_resources.Resource.create(
        {"service.name": "backend", "cloud.provider": "heroku"}
    )

    def __new__(cls):
        if not cls.initalized:
            cls.tracer = cls.create_tracer(cls)
            cls.meter = cls.create_meter(cls)
            cls.sentry_init(cls)
            cls.initalized = True
        return cls

    def create_tracer(cls):
        otel_trace_provider = otel_sdk_trace.TracerProvider(resource=cls.resource)
        otel_processor = otel_export.BatchSpanProcessor(
            otel_trace_exporter.OTLPSpanExporter(
                endpoint="https://api.honeycomb.io/v1/traces",
                headers={
                    "x-honeycomb-team": os.getenv("HONEYCOMB_API_KEY"),
                },
            )
        )
        otel_trace_provider.add_span_processor(otel_processor)
        otel_trace.set_tracer_provider(otel_trace_provider)
        tracer = otel_trace.get_tracer(__name__)
        return tracer

    def create_meter(cls):
        dotenv.load_dotenv()
        metric_reader = otel_metrics_export.PeriodicExportingMetricReader(
            otel_metric_exporter.OTLPMetricExporter(
                endpoint="https://api.honeycomb.io/v1/metrics",
                headers={
                    "x-honeycomb-team": os.getenv("HONEYCOMB_API_KEY"),
                },
            )
        )
        meter_provider = otel_sdk_metrics.MeterProvider(
            resource=cls.resource,
            metric_readers=[metric_reader],
        )
        otel_metrics.set_meter_provider(meter_provider)
        meter = otel_metrics.get_meter(__name__)
        return meter

    def sentry_init(cls):
        if os.getenv("PRODUCTION", "").lower().strip() == "true":
            sentry_sdk.init(
                dsn=os.getenv("SENTRY_DSN"),
                integrations=[
                    StarletteIntegration(),
                    FastApiIntegration(),
                ],
            )
