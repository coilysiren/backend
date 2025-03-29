import asyncio
import os

import fastapi
import fastapi.middleware.cors as cors
import fastapi.middleware.trustedhost as trustedhost
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
        with telemetry.tracer.start_as_current_span("http_request") as span:
            return await call_next(request)


class ErrorHandlingMiddleware(middleware.BaseHTTPMiddleware):
    """Middleware to handle exceptions and return JSON responses"""

    timeout: int

    def __init__(self, app, timeout: int):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(
        self,
        request: starlette.requests.Request,
        call_next: middleware.RequestResponseEndpoint,
    ) -> starlette.responses.Response:
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError as exc:
            logger.error("Unhandled exception", exc=exc, status_code=408)
            sentry_sdk.capture_exception(exc)
            return starlette.responses.JSONResponse(
                {"detail": "Request timed out"}, status_code=408
            )
        except Exception as exc:
            logger.error("Unhandled exception", exc=exc, status_code=500)
            sentry_sdk.capture_exception(exc)
            return starlette.responses.JSONResponse(
                {"detail": "Internal Server Error", "error": str(exc)},
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

    # TODO: the timeout isn't reliable because sync code can block it from being enforced.
    app.add_middleware(ErrorHandlingMiddleware, timeout=30)

    app.add_middleware(OpenTelemetryMiddleware)

    # Allow requests to come in from specific places (part 1)
    if os.getenv("PRODUCTION", "").lower().strip() == "true":
        app.add_middleware(
            cors.CORSMiddleware,
            allow_origins=[
                "https://coilysiren.me",
                "https://www.coilysiren.me",
                "https://api.coilysiren.me",
            ],
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
