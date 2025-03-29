import inspect
import logging
import math
import os

import dotenv
import fastapi
import opentelemetry.exporter.otlp.proto.http.trace_exporter as otel_trace_exporter
import opentelemetry.instrumentation.fastapi as otel_fastapi
import opentelemetry.sdk.resources as otel_resources
import opentelemetry.sdk.trace as otel_sdk_trace
import opentelemetry.sdk.trace.export as otel_export
import opentelemetry.trace as otel_trace

from . import bsky
from . import application

dotenv.load_dotenv()
(app, limiter) = application.init()
bsky_client = bsky.init()


@app.get("/")
@limiter.limit("10/second")
async def root(request: fastapi.Request):
    return ["hello world"]


@app.get("/bsky/{me}/followers")
@app.get("/bsky/{me}/followers/")
@limiter.limit("10/second")
async def bsky_followers(request: fastapi.Request, me: str):
    output = bsky.get_followers(bsky_client, me)
    return output


@app.get("/bsky/{me}/following")
@app.get("/bsky/{me}/following/")
@limiter.limit("10/second")
async def bsky_following(request: fastapi.Request, me: str):
    output = bsky.get_following(bsky_client, me)
    return output


@app.get("/bsky/{me}/following/handles")
@app.get("/bsky/{me}/following/handles/")
@limiter.limit("10/second")
async def bsky_following_handles(request: fastapi.Request, me: str):
    output = bsky.get_following_handles(bsky_client, me)
    return output


@app.get("/bsky/{me}/profile")
@app.get("/bsky/{me}/profile/")
@limiter.limit("10/second")
async def bsky_profile(request: fastapi.Request, me: str):
    output = bsky.get_profile(bsky_client, me)
    return output


@app.get("/bsky/{me}/mutuals")
@app.get("/bsky/{me}/mutuals/")
@limiter.limit("10/second")
async def bsky_mutuals(request: fastapi.Request, me: str):
    """People I follow who follow me back"""
    followers = bsky.get_followers(bsky_client, me)
    following = bsky.get_following(bsky_client, me)
    mutuals = {k: v for k, v in followers.items() if k in following}
    return mutuals


@app.get("/bsky/{me}/credibility/{them}")
@app.get("/bsky/{me}/credibility/{them}/")
@limiter.limit("10/second")
async def bsky_credibilty(request: fastapi.Request, me: str, them: str):
    """
    For some person I follow,
    show who lends 'credibility' to them in the form of a follow
    """
    lenders = bsky.credibilty(bsky_client, me, them)
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
    percent = bsky.credibilty_percent(bsky_client, me, them)
    return percent


@app.get("/bsky/{me}/recommendations")
@app.get("/bsky/{me}/recommendations/")
@limiter.limit("10/second")
async def bsky_recommendations(request: fastapi.Request, me: str):
    """
    For every person I follow,
    list people who they follow,
    returning the first page of a list.
    """
    (reccomendations, next_index) = bsky.recommendations(bsky_client, me, 0)
    return {
        "reccomendations": reccomendations,
        "next": next_index,
    }


@app.get("/bsky/{me}/recommendations/{index}")
@app.get("/bsky/{me}/recommendations/{index}/")
@limiter.limit("10/second")
async def bsky_recommendations_page(request: fastapi.Request, me: str, index: int):
    """
    For every person I follow,
    list people who they follow,
    returning the {index} page of a list.
    """
    (reccomendations, next_index) = bsky.recommendations(bsky_client, me, index)
    return {
        "reccomendations": reccomendations,
        "next": next_index,
    }
