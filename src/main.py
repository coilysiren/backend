import dotenv
import fastapi

from . import bksy
from . import application

dotenv.load_dotenv()
(app, limiter) = application.init()
bksy_client = bksy.init()


@app.get("/")
@limiter.limit("1/second")
async def root(request: fastapi.Request):
    return ["hello world"]


@app.get("/bksy/followers")
@app.get("/bksy/followers/")
@limiter.limit("1/second")
async def bksy_followers(request: fastapi.Request):
    handle = request.query_params.get("handle", "")
    if not handle:
        raise fastapi.HTTPException(status_code=400, detail="No handle provided")
    return bksy.get_followers(bksy_client, handle)


@app.get("/bksy/following")
@app.get("/bksy/following/")
@limiter.limit("1/second")
async def bksy_following(request: fastapi.Request):
    handle = request.query_params.get("handle", "")
    if not handle:
        raise fastapi.HTTPException(status_code=400, detail="No handle provided")
    return bksy.get_following(bksy_client, handle)
