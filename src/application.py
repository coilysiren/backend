import asyncio
import os

import fastapi
import fastapi.middleware.cors as cors
import fastapi.middleware.trustedhost as trustedhost
import slowapi
import slowapi.errors
import slowapi.util
import starlette.responses
import starlette.middleware.base as middleware


class TimeoutMiddleware(middleware.BaseHTTPMiddleware):
    def __init__(self, app, timeout: int = 5):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: fastapi.Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            return starlette.responses.JSONResponse({"detail": "Request timed out"}, status_code=408)


def init() -> tuple[fastapi.FastAPI, slowapi.Limiter]:
    app = fastapi.FastAPI()

    # Allow requests to come in from specific places (part 1)
    app.add_middleware(
        cors.CORSMiddleware,
        allow_origins=[
            "" if os.getenv("PRODUCTION") == "True" else "localhost",
            "https://coilysiren.me/",
            "https://api.coilysiren.me/",
        ],
    )

    # Allow requests to come in from specific places (part 2)
    app.add_middleware(
        trustedhost.TrustedHostMiddleware,
        allowed_hosts=[
            "" if os.getenv("PRODUCTION") == "True" else "localhost",
            "coilysiren.me",
            "api.coilysiren.me",
        ],
    )

    # Timeout requests after N seconds
    app.add_middleware(TimeoutMiddleware, timeout=30)

    # Configure rate limiting
    # docs: https://slowapi.readthedocs.io/en/latest/
    # pylint: disable=protected-access
    limiter = slowapi.Limiter(key_func=slowapi.util.get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(slowapi.errors.RateLimitExceeded, slowapi._rate_limit_exceeded_handler)  # type: ignore
    # pylint: enable=protected-access

    return app, limiter
