import os
import re
import typing
import requests
import time

import atproto  # type: ignore
import structlog

from . import cache
from . import telemetry as _telemetry

telemetry = _telemetry.Telemetry()
logger = structlog.get_logger()

# MAX_FOLLOWS_PAGES * 100 is the max number of follows to list
MAX_FOLLOWS_PAGES = 25

SUGGESTIONS_PER_PAGE = 10
MAX_SUGGESTION_PAGES = 10

POPULARITY_PER_PAGE = 50
MAX_POPULARITY_PAGES = 50


# class Bsky(object):

#     _client: atproto.Client
#     _client_refresh_interval: int = 60 * 60 * 8  # 8 hours
#     _client_last_refresh: int = 0

#     @property
#     def client(self) -> atproto.Client:
#         if not self._client:
#             self._client = init()

#         if time.time() - self._client_last_refresh > self._client_refresh_interval:
#             logger.info("refreshing bsky client")
#             self._client = init()
#             self._client_last_refresh = time.time()

#         return self._client


def init():
    client = atproto.Client("https://bsky.social")
    client.login(login=os.getenv("BSKY_USERNAME"), password=os.getenv("BSKY_PASSWORD"))
    return client


async def popularity(client: atproto.Client, me: str, index=0) -> tuple[dict[str, int], int]:
    """
    For every person I follow,
    list people who they follow,
    and aggregate that list to see how popular each person is.
    """
    next_index = index + POPULARITY_PER_PAGE
    my_following = await get_following_handles(client, me)
    my_following.sort()
    my_following_to_check = my_following[index:next_index]

    popularity_dict: dict[str, int] = {}

    # For everyone that I follow,
    for my_follow in my_following_to_check:

        # List of who they follow
        following = await get_following_handles(client, my_follow)

        # And remove the people I follow
        for thier_follow in following:
            thier_follow.strip().lower()
            if thier_follow and thier_follow != "handle.invalid" and thier_follow != "bsky.app":
                if popularity_dict.get(thier_follow) is None:
                    popularity_dict[thier_follow] = 1
                else:
                    popularity_dict[thier_follow] += 1

    # return -1 next index (indicating the we are done) if we are at the end of the list
    next_index = next_index if next_index < POPULARITY_PER_PAGE * MAX_POPULARITY_PAGES else -1

    return (popularity_dict, next_index)


async def suggestions(client: atproto.Client, me: str, index=0) -> tuple[list[str], int]:
    """
    For everyone that I follow,
    list who they follow that I don't follow.
    """
    next_index = index + SUGGESTIONS_PER_PAGE
    my_following = await get_following_handles(client, me)
    my_following.sort()
    my_following_to_check = my_following[index:next_index]

    suggestions = []

    # For everyone that I follow,
    for my_follow in my_following_to_check:

        # List of who they follow
        following = await get_following_handles(client, my_follow)

        # And remove the people I follow
        for thier_follow in following:
            thier_follow.strip().lower()
            if (
                thier_follow
                and thier_follow is not me
                and thier_follow not in my_following
                and thier_follow != "handle.invalid"
                and thier_follow != "bsky.app"
            ):

                # Then add them to the suggestions
                suggestions.append(thier_follow)

    # return -1 next index (indicating the we are done) if we are at the end of the list
    next_index = next_index if next_index < SUGGESTIONS_PER_PAGE * MAX_SUGGESTION_PAGES else -1

    return (suggestions, next_index)


async def get_profile(client: atproto.Client, handle: str) -> typing.Dict[str, dict]:
    def _get_profile_request():
        response = requests.get(
            "https://bsky.social/xrpc/app.bsky.actor.getProfile",
            params={"actor": handle},
            headers={"Authorization": f"Bearer {client._session.access_jwt}"},
            timeout=10,
        )
        response.raise_for_status()
        return response

    output = await cache.get_or_return_cached_request("bsky.get-profile", handle, _get_profile_request)
    return {output["did"]: output}


async def get_followers(client: atproto.Client, handle: str) -> typing.Dict[str, typing.Any]:
    def _get_followers_request():
        response = requests.get(
            "https://bsky.social/xrpc/app.bsky.graph.getFollowers",
            params={"actor": handle, "limit": 100},
            headers={"Authorization": f"Bearer {client._session.access_jwt}"},
            timeout=10,
        )
        response.raise_for_status()
        return response

    output = await cache.get_or_return_cached_request("bsky.get-followers", handle, _get_followers_request)
    follows = {profile["did"]: profile for profile in output.get("followers", [])}
    return follows


async def get_following(client: atproto.Client, handle: str) -> typing.Dict[str, typing.Any]:
    def _get_following_request():
        response = requests.get(
            "https://bsky.social/xrpc/app.bsky.graph.getFollows",
            params={"actor": handle, "limit": 100},
            headers={"Authorization": f"Bearer {client._session.access_jwt}"},
            timeout=10,
        )
        response.raise_for_status()
        return response

    output = await cache.get_or_return_cached_request("bsky.get-following", handle, _get_following_request)
    follows = {profile["did"]: profile for profile in output.get("follows", [])}
    return follows


async def get_following_handles(client: atproto.Client, handle: str) -> list[str]:
    def _get_following_handles_request():
        response = requests.get(
            "https://bsky.social/xrpc/app.bsky.graph.getFollows",
            params={"actor": handle, "limit": 100},
            headers={"Authorization": f"Bearer {client._session.access_jwt}"},
            timeout=10,
        )
        response.raise_for_status()
        return response

    output = await cache.get_or_return_cached_request(
        "bsky.get-following-handles", handle, _get_following_handles_request
    )
    return [profile["handle"] for profile in output.get("follows", [])]


async def get_author_feed(
    client: atproto.Client, handle: str, cursor: str = ""
) -> tuple[list[dict[str, typing.Any]], str]:
    def _get_author_feed_request():
        response = requests.get(
            "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed",
            params={"actor": handle, "limit": 100, "cursor": cursor},
            headers={"Authorization": f"Bearer {client._session.access_jwt}"},
            timeout=10,
        )
        response.raise_for_status()
        return response

    output = await cache.get_or_return_cached_request(
        f"bsky.get-author-feed-{cursor}", handle, _get_author_feed_request
    )
    return (output.get("feed", []), output.get("cursor", ""))


async def get_author_feed_text(client: atproto.Client, handle: str, cursor: str = "") -> tuple[list[str], str]:
    def _get_author_feed_text_request():
        response = requests.get(
            "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed",
            params={"actor": handle, "limit": 100, "filter": "posts_no_replies", "cursor": cursor},
            headers={"Authorization": f"Bearer {client._session.access_jwt}"},
            timeout=10,
        )
        response.raise_for_status()
        return response

    feed_data = await cache.get_or_return_cached_request(
        f"bsky.get-author-feed-text-{cursor}", handle, _get_author_feed_text_request
    )
    return ([post["post"]["record"]["text"] for post in feed_data.get("feed", [])], feed_data.get("cursor", ""))


async def get_author_feed_texts(client: atproto.Client, handle: str, pages: int = 1) -> list[str]:
    """
    Get the text of the author's feed, going back a number of pages.
    """
    page = 0
    texts = []
    cursor = ""
    while page < pages:
        page_texts, cursor = await get_author_feed_text(client, handle, cursor)
        print(f"cursor: {cursor}")
        texts += page_texts
        if not cursor:
            break
        page += 1
    return texts


def handle_scrubber(handle: str) -> str:
    # allow the following characters:
    # 1. a - z (lowercase or uppercase)
    # 2. 0 - 9 (numbers)
    # 3. . (period)
    # 4. _ (underscore)
    # 5. - (dash)
    # remove any characters that do not match the above rules
    # Use regex to filter allowed characters
    handle = re.sub(r"[^a-zA-Z0-9._-]", "", handle)
    return handle.strip().lower()
