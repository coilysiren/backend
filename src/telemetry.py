import os

import dotenv
import opentelemetry.exporter.otlp.proto.http.trace_exporter as otel_trace_exporter
import opentelemetry.sdk.resources as otel_resources
import opentelemetry.sdk.trace as otel_sdk_trace
import opentelemetry.sdk.trace.export as otel_export
import opentelemetry.trace as otel_trace
import sentry_sdk
import sentry_sdk.integrations.fastapi as sentry_fastapi
import sentry_sdk.integrations.starlette as sentry_starlette

dotenv.load_dotenv()


class Telemetry(object):
    # https://opentelemetry.io/docs/languages/python/instrumentation/

    initalized = False
    tracer: otel_trace.Tracer
    resource: otel_resources.Resource = otel_resources.Resource.create(
        {"service.name": "backend", "cloud.provider": "heroku"}
    )

    def __new__(cls):
        if not cls.initalized:
            cls.tracer = cls.create_tracer(cls)
            cls.sentry_init(cls)
            cls.initalized = True
        return cls

    def create_tracer(self):
        otel_trace_provider = otel_sdk_trace.TracerProvider(resource=self.resource)
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

    def sentry_init(self):
        # Init a real version of the sentry client, just to make sure its working.
        sentry_sdk.init(
            dsn=os.getenv("SENTRY_DSN"),
            integrations=[
                sentry_starlette.StarletteIntegration(),
                sentry_fastapi.FastApiIntegration(),
            ],
        )
        # Init a fake (empty) version of the sentry client, to avoid sending data locally.
        if os.getenv("PRODUCTION", "").lower().strip() != "true":
            sentry_sdk.init()
