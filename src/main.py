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


# TODO: integrations with external services I already have credentials for in sibling repos.
# Each of these should grow into a `src/<service>.py` module + routes here, mirroring the
# pattern used by `bsky.py`. Credentials should come from env vars loaded via dotenv.
#
# TODO(github): GitHub API integration. Used in ../website/scripts/fetch-now-data.ts for
#   commits, PRs, and starred repos via the `gh` CLI. Add /github/{user}/... endpoints
#   (recent commits, PRs, stars) using a GITHUB_TOKEN env var.
#
# TODO(youtube): YouTube Data API via Google OAuth. See ../website/scripts/youtube-auth.ts
#   and ../website/scripts/fetch-now-data.ts. Port the OAuth token flow and expose
#   /youtube/{channel}/... endpoints (recent uploads, watch history if available). Creds
#   live in SSM under /youtube/{client-id,client-secret,refresh-token}.
#
# TODO(reddit): Reddit public API (no auth). See ../website/scripts/fetch-now-data.ts.
#   Add /reddit/{user}/... endpoints (recent posts/comments).
#
# TODO(steam): Steam Web API. See ../website/scripts/fetch-now-data.ts. Creds live in
#   SSM under /steam/{web-api-key,steam-id-64}. Add /steam/{steamid}/... endpoints
#   (recently played, owned games, achievements).
#
# TODO(discord): Discord bot integration. See ../discord-bot/ (DISCORD_BOT_TOKEN). Decide
#   whether this backend should host a bot worker, or just expose webhook endpoints the
#   discord-bot process can call.
#
# TODO(anthropic): Anthropic API. Used in ../gauntlet (GAUNTLET_INSPECTOR_KEY). Add an
#   ANTHROPIC_API_KEY env var and an LLM helper module — useful for summarizing bsky
#   feeds, emoji summaries, etc. Enable prompt caching.
#
# TODO(openai): OpenAI API. Used in ../gauntlet (GAUNTLET_ATTACKER_KEY). Add OPENAI_API_KEY
#   for embeddings / fallback completions.
#
# TODO(aws): AWS via boto3. Used across ../infrastructure (eco.py, k8s.py, llama.py) for
#   SSM Parameter Store and S3. Consider pulling production secrets from SSM instead of
#   .env, and using S3 for cache/artifact storage (e.g. emoji-summary results, video).
#
# TODO(netlify): Netlify hosts ../website. Add a deploy-hook trigger endpoint so this
#   backend can kick a website rebuild when upstream data (bsky stats, etc.) changes.

otel_fastapi.FastAPIInstrumentor.instrument_app(app)
