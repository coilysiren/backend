import math

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


@app.get("/bsky/{me}/followers")
@app.get("/bsky/{me}/followers/")
@limiter.limit("1/second")
async def bsky_followers(request: fastapi.Request, me: str):
    output = bsky.get_followers(bsky_client, me)
    return output


@app.get("/bsky/{me}/following")
@app.get("/bsky/{me}/following/")
@limiter.limit("1/second")
async def bsky_following(request: fastapi.Request, me: str):
    output = bsky.get_following(bsky_client, me)
    return output


@app.get("/bsky/{me}/profile")
@app.get("/bsky/{me}/profile/")
@limiter.limit("1/second")
async def bsky_profile(request: fastapi.Request, me: str):
    output = bsky.get_profile(bsky_client, me)
    return output


@app.get("/bsky/{me}/mutuals")
@app.get("/bsky/{me}/mutuals/")
@limiter.limit("1/second")
async def bsky_mutuals(request: fastapi.Request, me: str):
    """People I follow who follow me back"""
    followers = bsky.get_followers(bsky_client, me)
    following = bsky.get_following(bsky_client, me)
    mutuals = {k: v for k, v in followers.items() if k in following}
    return mutuals


@app.get("/bsky/{me}/credibility/{them}")
@app.get("/bsky/{me}/credibility/{them}/")
@limiter.limit("1/second")
async def bsky_credibilty(request: fastapi.Request, me: str, them: str):
    """
    For some person I follow,
    show who lends 'credibility' to them in the form of a follow
    """
    lenders = bsky.credibilty(bsky_client, me, them)
    return lenders


@app.get("/bsky/{me}/credibility/{them}/percent")
@app.get("/bsky/{me}/credibility/{them}/percent/")
@limiter.limit("1/second")
async def bsky_credibilty_percent(request: fastapi.Request, me: str, them: str):
    """
    For some person I follow,
    show who lends 'credibility' to them in the form of a follow,
    as of of a percent of their followers.
    100% credibility would mean that all of their followers are people I follow.
    """
    percent = bsky.credibilty_percent(bsky_client, me, them)
    return str(percent).split(".", maxsplit=1)[0] + "%"


@app.get("/bsky/{me}/recommendations")
@app.get("/bsky/{me}/recommendations/")
@limiter.limit("1/second")
async def bsky_recommendations(request: fastapi.Request, me: str):
    """
    For some person I follow,
    show who lends 'credibility' to them in the form of a follow
    """
    reccomendations = bsky.recommendations(bsky_client, me)
    return reccomendations


otel_fastapi.FastAPIInstrumentor.instrument_app(app)
