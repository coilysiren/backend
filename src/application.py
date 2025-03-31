import asyncio
import os

import atproto_client.exceptions  # type: ignore
import atproto_client.models.common as atproto_models  # type: ignore
import fastapi
import fastapi.middleware.cors as cors
import fastapi.middleware.trustedhost as trustedhost
import opentelemetry.trace as otel_trace
import sentry_sdk
import slowapi
import slowapi.errors
import slowapi.util
import starlette.middleware.base as middleware
import starlette.requests
import starlette.responses
import structlog

from . import telemetry

telemetry = telemetry.Telemetry()
logger = structlog.get_logger()


class OpenTelemetryMiddleware(middleware.BaseHTTPMiddleware):
    """Middleware to handle OpenTelemetry tracing for incoming HTTP requests."""

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(
        self,
        request: starlette.requests.Request,
        call_next: middleware.RequestResponseEndpoint,
    ) -> starlette.responses.Response:
        with telemetry.tracer.start_as_current_span("OpenTelemetryMiddleware") as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.request.path", request.url.path)

            for key, value in request.query_params.items():
                span.set_attribute(f"http.request.query.{key}", value)

            for key, value in request.path_params.items():
                span.set_attribute(f"http.request.path.{key}", value)

            response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)
            return response


class ErrorHandlingMiddleware(middleware.BaseHTTPMiddleware):
    """Middleware to handle exceptions and return JSON responses"""

    timeout: int

    def __init__(self, app, timeout: int):
        super().__init__(app)
        self.timeout = timeout

    def _capture_exception(self, span: otel_trace.Span, exc: Exception) -> None:
        sentry_sdk.capture_exception(exc)
        span.set_status(otel_trace.StatusCode.ERROR, str(exc))
        span.set_attribute("exception.type", type(exc).__name__)
        span.set_attribute("exception.message", str(exc))
        span.record_exception(exc)

    async def dispatch(
        self,
        request: starlette.requests.Request,
        call_next: middleware.RequestResponseEndpoint,
    ) -> starlette.responses.Response:
        with telemetry.tracer.start_as_current_span("ErrorHandlingMiddleware") as span:
            try:
                return await asyncio.wait_for(call_next(request), timeout=self.timeout)

            # Atproto can return specific errors that we want to handle gracefully.
            # These error types were enumerated by looking at the type annotations.
            except atproto_client.exceptions.RequestErrorBase as exc:
                self._capture_exception(span, exc)

                response = exc.response
                if response is None:
                    message = "unknown atproto error"
                    logger.error(message, exc=exc, status_code=500)
                    return starlette.responses.JSONResponse(
                        {"detail": message},
                        status_code=500,
                    )

                elif type(response.content) is atproto_models.XrpcError:
                    message = "generic xrpcerror error"
                    logger.error(
                        message,
                        exc=exc,
                        status_code=response.status_code,
                    )
                    return starlette.responses.JSONResponse(
                        {
                            "detail": message,
                            "error": response.content.message,
                        },
                        status_code=response.status_code,
                    )

                else:
                    message = "generic atproto error"
                    logger.info(
                        message,
                        exc=exc,
                        status_code=response.status_code,
                    )
                    return starlette.responses.JSONResponse(
                        {"detail": message, "error": str(response.content)},
                        status_code=response.status_code,
                    )

            # handle any kind of timeout errors, note that we enforce the timeouts
            except asyncio.TimeoutError as exc:
                self._capture_exception(span, exc)

                message = "request timed out"
                logger.error(message, exc=exc, status_code=408)
                return starlette.responses.JSONResponse({"detail": message}, status_code=408)

            # handle other exceptions that may occur during request processing
            except Exception as exc:
                self._capture_exception(span, exc)

                message = "internal server error"
                logger.error(message, exc=exc, status_code=500)
                return starlette.responses.JSONResponse(
                    {"detail": message, "error": str(exc)},
                    status_code=500,
                )


def init() -> tuple[fastapi.FastAPI, slowapi.Limiter]:
    app = fastapi.FastAPI()

    ####################
    # START MIDDLEWARE #
    ####################

    # This next section is for middleware. They are numbered to help explain
    # The order in which they are executed.
    #
    # The middleware is executed "top to bottom" on the way in,
    # and "bottom to top" on the way out.
    #
    # See example here:
    # https://github.com/encode/starlette/issues/479#issuecomment-1595113897

    app.add_middleware(ErrorHandlingMiddleware, timeout=30)

    app.add_middleware(OpenTelemetryMiddleware)

    # Allow requests to come in from specific places (part 1)
    app.add_middleware(
        cors.CORSMiddleware,
        allow_origins=(
            [
                "https://coilysiren.me",
                "https://www.coilysiren.me",
                "https://api.coilysiren.me",
            ]
            if os.getenv("PRODUCTION", "").lower().strip() == "true"
            else ["*"]
        ),
    )

    # Allow requests to come in from specific places (part 2)
    if os.getenv("PRODUCTION", "").lower().strip() == "true":
        app.add_middleware(
            trustedhost.TrustedHostMiddleware,
            allowed_hosts=[
                "coilysiren.me",
                "api.coilysiren.me",
            ],
        )

    ##################
    # END MIDDLEWARE #
    ##################

    # Configure rate limiting
    # docs: https://slowapi.readthedocs.io/en/latest/
    # pylint: disable=protected-access
    limiter = slowapi.Limiter(key_func=slowapi.util.get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(slowapi.errors.RateLimitExceeded, slowapi._rate_limit_exceeded_handler)  # type: ignore
    # pylint: enable=protected-access

    return app, limiter
