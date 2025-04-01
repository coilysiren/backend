import json
import sys

import dotenv
import invoke
import requests  # type: ignore
import structlog

from . import bsky as _bsky
from . import cache


dotenv.load_dotenv()
bsky_client = _bsky.init()
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),  # logs need to get to stderr so jq can parse stdout
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
def bsky(ctx: invoke.Context, path: str, kwargs: str):
    # https://docs.bsky.app/docs/category/http-reference
    cache_suffix = f"tasks.bsky-{path}-{kwargs}".replace(" ", "-")
    kwargs = _parse_kwargs(kwargs)
    token = bsky_client._session.access_jwt
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    response = cache.get_or_return_cache(
        "tasks.bsky",
        cache_suffix,
        lambda: requests.get(f"https://bsky.social/xrpc/{path}", headers=headers, timeout=30, params=kwargs),
    )
    print(json.dumps(response.json(), indent=2))
