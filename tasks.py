import asyncio
import json
import sys
import typing

import dotenv
import invoke
import requests  # type: ignore
import structlog

from src import bsky, cache
from src import worker

dotenv.load_dotenv()
bsky_instance = bsky.Bsky()

# Send our logs to stderr so jq can parse stdout.
# This only needs to happen here, inside of the CLI entrypoint.
# That is, as opposed to the REST API entrypoint.
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)


def _parse_kwargs(input_str: str) -> dict[str, typing.Any]:
    """Parses a CLI-friendly 'key1 value1 key2 value2' string into a dictionary."""
    tokens = input_str.split()
    parsed_data: dict[str, typing.Any] = {}

    i = 0
    while i < len(tokens):
        key = tokens[i].strip("--")
        value = tokens[i + 1] if i + 1 < len(tokens) else None

        if key in parsed_data:
            if isinstance(parsed_data[key], list):
                parsed_data[key].append(value)
            else:
                parsed_data[key] = [parsed_data[key], value]
        else:
            parsed_data[key] = value

        i += 2  # Move to the next key

    return parsed_data


@invoke.task
def clear_cache(ctx: invoke.Context, suffix: str):
    cache.delete_keys(suffix)


@invoke.task
def bsky_cli(ctx: invoke.Context, path: str, kwargs: str = ""):
    cache_suffix = f"tasks.bsky-{path}-{kwargs}".replace(" ", "-")

    def _get_request():
        response = requests.get(
            f"https://bsky.social/xrpc/{path}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {bsky_instance.client._session.access_jwt}",
            },
            timeout=30,
            params=_parse_kwargs(kwargs),
        )
        response.raise_for_status()
        return response

    response = asyncio.run(
        cache.get_or_return_cached_request(
            "tasks.bsky",
            cache_suffix,
            _get_request,
        )
    )
    print(json.dumps(response, indent=2))


@invoke.task
def bsky_get_author_feed_texts(ctx: invoke.Context, handle: str, pages: int = 1):
    """Get the author's feed texts."""
    output = asyncio.run(
        bsky.get_author_feed_texts(
            bsky_instance.client,
            handle,
            pages,
        )
    )
    print(json.dumps(output, indent=2))


@invoke.task
def bsky_emoji_summary(ctx: invoke.Context, handle: str, num_keywords: int = 25, num_feed_pages: int = 25):
    """Process emoji summary for a user's posts."""
    task_id = f"emoji-summary-{handle}"
    results = asyncio.run(
        worker.process_emoji_summary(bsky_instance.client, task_id, handle, num_keywords, num_feed_pages)
    )
    print(json.dumps(results, indent=2))


@invoke.task
def stream_video(path: str, chunk_size: int = 25 * 1024):
    with open(path, "rb") as f:
        size = f.__sizeof__()
        read_size = 0

        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk
            read_size += chunk_size
            print(f"{read_size / size * 100}%")
