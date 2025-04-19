import asyncio
import datetime
import os
import urllib.parse
import uuid

import dotenv
import fastapi
import opentelemetry.instrumentation.fastapi as otel_fastapi
import structlog
import structlog.processors

from . import application, bsky, cache, worker, streaming

dotenv.load_dotenv()
(app, limiter) = application.init()
bsky_instance = bsky.Bsky()

structlog.configure(
    processors=[
        structlog.processors.JSONRenderer(sort_keys=True),
    ]
)


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


@app.get("/streaming")
@app.get("/streaming/")
async def streaming_test():
    return fastapi.responses.StreamingResponse(streaming.testing(), media_type="text/plain")


# @app.get("/video")
# @app.get("/video/")
# async def video():
#     return fastapi.responses.FileResponse("bunny.webm")


@app.get("/bsky/{handle}/followers")
@app.get("/bsky/{handle}/followers/")
@limiter.limit("10/second")
async def bsky_followers(request: fastapi.Request, handle: str):
    handle = bsky.handle_scrubber(handle)
    output = await bsky.get_followers(bsky_instance.client, handle)
    return output


@app.get("/bsky/{handle}/following")
@app.get("/bsky/{handle}/following/")
@limiter.limit("10/second")
async def bsky_following(request: fastapi.Request, handle: str):
    handle = bsky.handle_scrubber(handle)
    output = await bsky.get_following(bsky_instance.client, handle)
    return output


@app.get("/bsky/{handle}/following/handles")
@app.get("/bsky/{handle}/following/handles/")
@limiter.limit("10/second")
async def bsky_following_handles(request: fastapi.Request, handle: str):
    handle = bsky.handle_scrubber(handle)
    output = await bsky.get_following_handles(bsky_instance.client, handle)
    return output


@app.get("/bsky/{handle}/profile")
@app.get("/bsky/{handle}/profile/")
@limiter.limit("10/second")
async def bsky_profile(request: fastapi.Request, handle: str):
    handle = bsky.handle_scrubber(handle)
    output = await bsky.get_profile(bsky_instance.client, handle)
    return output


@app.get("/bsky/{handle}/mutuals")
@app.get("/bsky/{handle}/mutuals/")
@limiter.limit("10/second")
async def bsky_mutuals(request: fastapi.Request, handle: str):
    """People I follow who follow me back"""
    handle = bsky.handle_scrubber(handle)
    followers = await bsky.get_followers(bsky_instance.client, handle)
    following = await bsky.get_following(bsky_instance.client, handle)
    mutuals = {k: v for k, v in followers.items() if k in following}
    return mutuals


@app.get("/bsky/{handle}/popularity")
@app.get("/bsky/{handle}/popularity/")
async def bluesky_popularity(request: fastapi.Request, handle: str):
    """
    For every person I follow,
    list people who they follow,
    and aggregate that list to see how popular each person is.
    """
    handle = bsky.handle_scrubber(handle)
    (popularity, next_index) = await bsky.popularity(bsky_instance.client, handle, 0)
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
    (popularity, next_index) = await bsky.popularity(bsky_instance.client, handle, index)
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
    (suggestions, next_index) = await bsky.suggestions(bsky_instance.client, handle, 0)
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
    (suggestions, next_index) = await bsky.suggestions(bsky_instance.client, handle, index)
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
    (feed, cursor) = await bsky.get_author_feed(bsky_instance.client, handle, request.query_params.get("cursor", ""))
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
        bsky_instance.client, handle, request.query_params.get("cursor", "")
    )
    return {
        "feed": feed,
        "next": cursor,
    }


@app.get("/bsky/{handle}/emoji-summary")
@app.get("/bsky/{handle}/emoji-summary/")
@limiter.limit("10/second")
async def bsky_emoji_summary_start(
    request: fastapi.Request, handle: str, num_keywords: int = 25, num_feed_pages: int = 25
):
    """
    Start generating an emoji summary for a user's posts.
    Returns a task ID that can be used to check the status.
    """
    handle = bsky.handle_scrubber(handle)

    # Store initial status in cache
    async_task_data = cache.create_or_return_async_task_data(
        "emoji-summary",
        handle,
    )

    # If the task ID is not found, start the task in the background
    if async_task_data.task_data is None:
        asyncio.create_task(
            worker.process_emoji_summary(
                bsky_instance.client, async_task_data.task_id, handle, num_keywords, num_feed_pages
            )
        )

    return async_task_data.to_dict()


otel_fastapi.FastAPIInstrumentor.instrument_app(app)
