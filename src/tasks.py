import asyncio
import os
import json
import sys

import dotenv
import invoke
import requests  # type: ignore
import structlog

from . import bsky
from . import cache
from . import data_science as _data_science

dotenv.load_dotenv()
bsky_client = bsky.init()
data_science_client = _data_science.DataScienceClient()
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(
        file=sys.stderr
    ),  # logs need to get to stderr so jq can parse stdout
)


def _parse_kwargs(input_str: str) -> dict[str, any]:
    """Parses a CLI-friendly 'key1 value1 key2 value2' string into a dictionary."""
    tokens = input_str.split()
    parsed_data = {}

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
    kwargs = _parse_kwargs(kwargs)
    token = bsky_client._session.access_jwt
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    response = asyncio.run(
        cache.get_or_return_cached_request(
            "tasks.bsky",
            cache_suffix,
            lambda: requests.get(
                f"https://bsky.social/xrpc/{path}",
                headers=headers,
                timeout=30,
                params=kwargs,
            ),
        )
    )
    print(json.dumps(response, indent=2))


@invoke.task
def bsky_get_author_feed_texts(ctx: invoke.Context, handle: str, pages: int = 1):
    """Get the author's feed texts."""
    output = asyncio.run(
        bsky.get_author_feed_texts(
            bsky_client,
            handle,
            pages,
        )
    )
    print(json.dumps(output, indent=2))


@invoke.task
def bsky_emoji_summary(
    ctx: invoke.Context, handle: str, num_keywords=25, num_feed_pages=25
):
    # Get the author's feed texts
    text_lines = asyncio.run(
        bsky.get_author_feed_texts(bsky_client, handle, num_feed_pages)
    )
    text_joined = "\n".join(text_lines)

    # Get the keywords and emoji match scores
    keywords = _data_science.extract_keywords(
        data_science_client, text_joined, num_keywords
    )
    emoji_match_scores = _data_science.get_emoji_match_scores(
        data_science_client, keywords
    )
    emoji_descriptions = _data_science.join_description_and_emoji_score(
        text_lines, emoji_match_scores
    )

    # Display the results
    print()
    print(f"{handle} talks about...")
    print()

    for description in emoji_descriptions:
        print(">", description[0], description[1])
        print()
        print(description[2])
        print()
