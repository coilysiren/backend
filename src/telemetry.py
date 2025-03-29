import dotenv
import os

import opentelemetry.exporter.otlp.proto.http.trace_exporter as otel_trace_exporter
import opentelemetry.sdk.resources as otel_resources
import opentelemetry.sdk.trace as otel_sdk_trace
import opentelemetry.sdk.trace.export as otel_export
import opentelemetry.trace as otel_trace


class Telemetry(object):
    # https://opentelemetry.io/docs/languages/python/instrumentation/

    tracer: otel_trace.Tracer = None

    def __new__(cls):
        if cls.tracer is None:
            cls.tracer = cls.create_tracer()
        return cls

    def create_tracer():
        dotenv.load_dotenv()
        otel_resource = otel_resources.Resource.create({"service.name": "backend"})
        otel_trace_provider = otel_sdk_trace.TracerProvider(resource=otel_resource)
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
