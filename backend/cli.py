"""Operator-facing dev/debug CLI. Replaces the retired pyinvoke tasks.py.

Invoke via `uv run python -m backend.cli <subcommand>` or one of the
`make` targets that wrap each subcommand. Operator-facing verbs are also
exposed through `.coily/coily.yaml`.
"""

import argparse
import asyncio
import json
import sys
import typing

import dotenv
import requests  # type: ignore
import structlog

from backend import bsky, cache, worker


def _parse_kwargs(input_str: str) -> dict[str, typing.Any]:
    """Parses a CLI-friendly 'key1 value1 key2 value2' string into a dictionary."""
    tokens = input_str.split()
    parsed_data: dict[str, typing.Any] = {}

    i = 0
    while i < len(tokens):
        key = tokens[i].lstrip("-")
        value = tokens[i + 1] if i + 1 < len(tokens) else None

        if key in parsed_data:
            if isinstance(parsed_data[key], list):
                parsed_data[key].append(value)
            else:
                parsed_data[key] = [parsed_data[key], value]
        else:
            parsed_data[key] = value

        i += 2

    return parsed_data


def cmd_clear_cache(_bsky: "bsky.Bsky", args: argparse.Namespace) -> None:
    cache.delete_keys(args.suffix)


def cmd_bsky_cli(bsky_instance: "bsky.Bsky", args: argparse.Namespace) -> None:
    cache_suffix = f"tasks.bsky-{args.path}-{args.kwargs}".replace(" ", "-")

    def _get_request():
        response = requests.get(
            f"https://bsky.social/xrpc/{args.path}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {bsky_instance.client._session.access_jwt}",
            },
            timeout=30,
            params=_parse_kwargs(args.kwargs),
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


def cmd_bsky_get_author_feed_texts(bsky_instance: "bsky.Bsky", args: argparse.Namespace) -> None:
    output = asyncio.run(
        bsky.get_author_feed_texts(
            bsky_instance.client,
            args.handle,
            args.pages,
        )
    )
    print(json.dumps(output, indent=2))


def cmd_bsky_emoji_summary(bsky_instance: "bsky.Bsky", args: argparse.Namespace) -> None:
    task_id = f"emoji-summary-{args.handle}"
    results = asyncio.run(
        worker.process_emoji_summary(
            bsky_instance.client,
            task_id,
            args.handle,
            args.num_keywords,
            args.num_feed_pages,
        )
    )
    print(json.dumps(results, indent=2))


def cmd_stream_video(_bsky: "bsky.Bsky", args: argparse.Namespace) -> None:
    chunk_size = args.chunk_size * 1024  # Convert KB
    print(f"Streaming video from {args.path} with chunk size {chunk_size}")

    with open(args.path, "rb") as f:
        print(f"Reading file {args.path}")
        f.seek(0, 2)  # Seek to end
        size = f.tell()  # Get position (file size)
        f.seek(0)  # Seek back to start
        read_size = 0

        while True:
            progress = (read_size / size * 100) if size > 0 else 0
            print(f"Progress: {progress:.2f}%")
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sys.stdout.buffer.write(chunk)
            sys.stdout.flush()
            read_size += len(chunk)

    print("\nDone")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="backend-cli")
    subs = parser.add_subparsers(dest="cmd", required=True)

    p = subs.add_parser("clear-cache", help="Delete cache keys with the given suffix.")
    p.add_argument("--suffix", required=True)
    p.set_defaults(func=cmd_clear_cache)

    p = subs.add_parser("bsky-cli", help="Call a Bluesky XRPC endpoint with caching.")
    p.add_argument("--path", required=True)
    p.add_argument("--kwargs", default="")
    p.set_defaults(func=cmd_bsky_cli)

    p = subs.add_parser("bsky-get-author-feed-texts", help="Dump an author's feed texts.")
    p.add_argument("--handle", required=True)
    p.add_argument("--pages", type=int, default=1)
    p.set_defaults(func=cmd_bsky_get_author_feed_texts)

    p = subs.add_parser("bsky-emoji-summary", help="Run the emoji-summary NLP job for a handle.")
    p.add_argument("--handle", required=True)
    p.add_argument("--num-keywords", type=int, default=25)
    p.add_argument("--num-feed-pages", type=int, default=25)
    p.set_defaults(func=cmd_bsky_emoji_summary)

    p = subs.add_parser("stream-video", help="Stream a local video file demo.")
    p.add_argument("--path", required=True)
    p.add_argument("--chunk-size", type=int, default=1)
    p.set_defaults(func=cmd_stream_video)

    return parser


def main() -> None:
    dotenv.load_dotenv()

    # Send our logs to stderr so jq can parse stdout. Only needed inside this
    # CLI entrypoint, not the REST API entrypoint.
    structlog.configure(
        processors=[
            structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )

    parser = _build_parser()
    args = parser.parse_args()
    bsky_instance = bsky.Bsky()
    args.func(bsky_instance, args)


if __name__ == "__main__":
    main()
