import os

import dotenv
import fastapi
import fastapi.middleware.cors as cors
import fastapi.middleware.trustedhost as trustedhost
import slowapi
import slowapi.errors
import slowapi.util

dotenv.load_dotenv()

app = fastapi.FastAPI()
app.add_middleware(
    cors.CORSMiddleware,
    allow_origins=[
        "" if os.getenv("PRODUCTION") == "True" else "localhost",
        "https://coilysiren.me/",
        "https://api.coilysiren.me/",
    ],
)
app.add_middleware(
    trustedhost.TrustedHostMiddleware,
    allowed_hosts=[
        "" if os.getenv("PRODUCTION") == "True" else "localhost",
        "coilysiren.me",
        "api.coilysiren.me",
    ],
)

limiter = slowapi.Limiter(key_func=slowapi.util.get_remote_address)
app.state.limiter = limiter
# pylint: disable=protected-access
# The docs for slowapi reccomend this... for whatever reason
# docs: https://slowapi.readthedocs.io/en/latest/
app.add_exception_handler(slowapi.errors.RateLimitExceeded, slowapi._rate_limit_exceeded_handler)  # type: ignore
# pylint: enable=protected-access


@app.get("/")
@limiter.limit("1/second")
async def root(request: fastapi.Request):
    return {"hello world": 100}
