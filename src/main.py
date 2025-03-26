import dotenv
import fastapi

from . import bsky
from . import application

dotenv.load_dotenv()
(app, limiter) = application.init()
bsky_client = bsky.init()


@app.get("/")
@limiter.limit("1/second")
async def root(request: fastapi.Request):
    return ["hello world"]


@app.get("/bsky/followers")
@app.get("/bsky/followers/")
@limiter.limit("1/second")
async def bsky_followers(request: fastapi.Request):
    handle = request.query_params.get("handle", "")
    if not handle:
        raise fastapi.HTTPException(status_code=400, detail="No handle provided")
    return bsky.get_followers(bsky_client, handle)


@app.get("/bsky/following")
@app.get("/bsky/following/")
@limiter.limit("1/second")
async def bsky_following(request: fastapi.Request):
    handle = request.query_params.get("handle", "")
    if not handle:
        raise fastapi.HTTPException(status_code=400, detail="No handle provided")
    return bsky.get_following(bsky_client, handle)
