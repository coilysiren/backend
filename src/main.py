import dotenv
import fastapi
import opentelemetry.instrumentation.fastapi as otel_fastapi

from . import application
from . import bsky
from . import cache

dotenv.load_dotenv()
(app, limiter) = application.init()
bsky_client = bsky.init()


@app.get("/")
@limiter.limit("10/second")
async def root(request: fastapi.Request):
    return ["hello", "world"]


@app.get("/explode")
@app.get("/explode/")
async def trigger_error():
    return 1 / 0


@app.get("/cache/clear/{suffix}")
@app.get("/cache/clear/{suffix}/")
async def cache_clear(request: fastapi.Request, suffix: str):
    """
    Clear the cache for a given suffix.
    """
    cache.delete_keys(suffix)
    return {"status": "ok"}


@app.get("/bsky/{handle}/followers")
@app.get("/bsky/{handle}/followers/")
@limiter.limit("10/second")
async def bsky_followers(request: fastapi.Request, handle: str):
    handle = bsky.handle_scrubber(handle)
    output = await bsky.get_followers(bsky_client, handle)
    return output


@app.get("/bsky/{handle}/following")
@app.get("/bsky/{handle}/following/")
@limiter.limit("10/second")
async def bsky_following(request: fastapi.Request, handle: str):
    handle = bsky.handle_scrubber(handle)
    output = await bsky.get_following(bsky_client, handle)
    return output


@app.get("/bsky/{handle}/following/handles")
@app.get("/bsky/{handle}/following/handles/")
@limiter.limit("10/second")
async def bsky_following_handles(request: fastapi.Request, handle: str):
    handle = bsky.handle_scrubber(handle)
    output = await bsky.get_following_handles(bsky_client, handle)
    return output


@app.get("/bsky/{handle}/profile")
@app.get("/bsky/{handle}/profile/")
@limiter.limit("10/second")
async def bsky_profile(request: fastapi.Request, handle: str):
    handle = bsky.handle_scrubber(handle)
    output = await bsky.get_profile(bsky_client, handle)
    return output


@app.get("/bsky/{handle}/mutuals")
@app.get("/bsky/{handle}/mutuals/")
@limiter.limit("10/second")
async def bsky_mutuals(request: fastapi.Request, handle: str):
    """People I follow who follow me back"""
    handle = bsky.handle_scrubber(handle)
    followers = await bsky.get_followers(bsky_client, handle)
    following = await bsky.get_following(bsky_client, handle)
    mutuals = {k: v for k, v in followers.items() if k in following}
    return mutuals


@app.get("/bsky/{me}/credibility/{them}")
@app.get("/bsky/{me}/credibility/{them}/")
@limiter.limit("10/second")
async def bsky_credibilty(request: fastapi.Request, handle: str, them: str):
    """
    For some person I follow,
    show who lends 'credibility' to them in the form of a follow
    """
    handle = bsky.handle_scrubber(handle)
    lenders = await bsky.credibilty(bsky_client, handle, them)
    return lenders


@app.get("/bsky/{me}/credibility/{them}/percent")
@app.get("/bsky/{me}/credibility/{them}/percent/")
@limiter.limit("10/second")
async def bsky_credibilty_percent(request: fastapi.Request, me: str, them: str):
    """
    For some person I follow,
    show who lends 'credibility' to them in the form of a follow,
    as of of a percent of their followers.
    1 credibility would mean that all of their followers are people I follow.
    """
    me = bsky.handle_scrubber(me)
    them = bsky.handle_scrubber(them)
    percent = await bsky.credibilty_percent(bsky_client, me, them)
    return percent


@app.get("/bsky/{handle}/popularity")
@app.get("/bsky/{handle}/popularity/")
async def bluesky_popularity(request: fastapi.Request, handle: str):
    """
    For every person I follow,
    list people who they follow,
    and aggregate that list to see how popular each person is.
    """
    handle = bsky.handle_scrubber(handle)
    (popularity, next_index) = await bsky.popularity(bsky_client, handle, 0)
    return {
        "popularity": popularity,
        "next": next_index,
    }


@app.get("/bsky/{handle}/popularity/{index}")
@app.get("/bsky/{handle}/popularity/{index}/")
async def bluesky_popularity_page(request: fastapi.Request, handle: str, index: int):
    """
    For every person I follow,
    list people who they follow,
    and aggregate that list to see how popular each person is.
    This returns the {index} page of the popularity list.
    """
    handle = bsky.handle_scrubber(handle)
    (popularity, next_index) = await bsky.popularity(bsky_client, handle, index)
    return {
        "popularity": popularity,
        "next": next_index,
    }


@app.get("/bsky/{handle}/suggestions")
@app.get("/bsky/{handle}/suggestions/")
@limiter.limit("10/second")
async def bsky_suggestions(request: fastapi.Request, handle: str):
    """
    For every person I follow,
    list people who they follow,
    returning the first page of a list.
    """
    handle = bsky.handle_scrubber(handle)
    (suggestions, next_index) = await bsky.suggestions(bsky_client, handle, 0)
    return {
        "suggestions": suggestions,
        "next": next_index,
    }


@app.get("/bsky/{handle}/suggestions/{index}")
@app.get("/bsky/{handle}/suggestions/{index}/")
@limiter.limit("10/second")
async def bsky_suggestions_page(request: fastapi.Request, handle: str, index: int):
    """
    For every person I follow,
    list people who they follow,
    returning the {index} page of a list.
    """
    handle = bsky.handle_scrubber(handle)
    (suggestions, next_index) = await bsky.suggestions(bsky_client, handle, index)
    return {
        "suggestions": suggestions,
        "next": next_index,
    }


@app.get("/bsky/{handle}/feed")
@app.get("/bsky/{handle}/feed/")
@limiter.limit("10/second")
async def bsky_author_feed(request: fastapi.Request, handle: str):
    """
    Get my posts
    """
    handle = bsky.handle_scrubber(handle)
    (feed, cursor) = await bsky.get_author_feed(
        bsky_client, handle, request.query_params.get("cursor", None)
    )
    return {
        "feed": feed,
        "next": cursor,
    }


@app.get("/bsky/{handle}/feed/text")
@app.get("/bsky/{handle}/feed/text/")
@limiter.limit("10/second")
async def bsky_author_feed_text(request: fastapi.Request, handle: str):
    """
    Get my posts
    """
    handle = bsky.handle_scrubber(handle)
    (feed, cursor) = await bsky.get_author_feed_text(
        bsky_client, handle, request.query_params.get("cursor", None)
    )
    return {
        "feed": feed,
        "next": cursor,
    }


otel_fastapi.FastAPIInstrumentor.instrument_app(app)
