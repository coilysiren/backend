import dotenv
import fastapi
import opentelemetry.instrumentation.fastapi as otel_fastapi

from . import bsky
from . import application

dotenv.load_dotenv()
(app, limiter) = application.init()
bsky_client = bsky.init()


@app.get("/")
@limiter.limit("1/second")
async def root(request: fastapi.Request):
    return ["hello world"]


@app.get("/bsky/followers/{handle}")
@app.get("/bsky/followers/{handle}/")
@limiter.limit("1/second")
async def bsky_followers(request: fastapi.Request, handle: str):
    profile = bsky_client.get_profile(handle)
    output = bsky.get_followers(bsky_client, handle, profile.did)
    return output


@app.get("/bsky/following/{handle}")
@app.get("/bsky/following/{handle}/")
@limiter.limit("1/second")
async def bsky_following(request: fastapi.Request, handle: str):
    profile = bsky_client.get_profile(handle)
    output = bsky.get_following(bsky_client, handle, profile.did)
    return output


otel_fastapi.FastAPIInstrumentor.instrument_app(app)
