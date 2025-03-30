import os
import typing

import atproto  # type: ignore
import atproto_client.exceptions
import structlog

from . import telemetry

telemetry = telemetry.Telemetry()
logger = structlog.get_logger()
cache: typing.Dict[str, typing.Any] = {}

# MAX_FOLLOWS_PAGES * FOLLOWS_PER_PAGE is the max number of follows to list
FOLLOWS_PER_PAGE = 100  # the max
MAX_FOLLOWS_PAGES = 10

# MAX_RECC_PAGES * RECS_PER_PAGE * MAX_FOLLOWS_PAGES * FOLLOWS_PER_PAGE is the max number of suggestions to list
RECS_PER_PAGE = 10
MAX_RECC_PAGES = 10


def init():
    client = atproto.Client("https://bsky.social")
    client.login(login=os.getenv("BSKY_USERNAME"), password=os.getenv("BSKY_PASSWORD"))
    return client


def suggestions(client: atproto.Client, me: str, index=0) -> tuple[list[str], int]:
    """
    For everyone that I follow,
    list who they follow that I don't follow.
    """
    next_index = index + RECS_PER_PAGE
    my_following = get_following_handles(client, me)
    my_following.sort()
    my_following = my_following[index:next_index]

    suggestions = []

    # For everyone that I follow,
    for my_follow in my_following:

        # List of who they follow
        following = get_following_handles(client, my_follow)

        # And remove the people I follow
        for thier_follow in following:
            if thier_follow not in my_following:

                # Then add them to the suggestions
                suggestions.append(thier_follow)

    # return -1 next index (indicating the we are done) if we are at the end of the list
    next_index = next_index if next_index < RECS_PER_PAGE * MAX_RECC_PAGES else -1

    return (suggestions, next_index)


def credibilty_percent(client: atproto.Client, me: str, them: str) -> float:
    """
    For some person I follow,
    show who lends 'credibility' to them in the form of a follow,
    as of of a percent of their followers.
    1 (eg. 100%) credibility would mean that all of their followers are people I follow.
    """
    thier_followers = get_followers(client, them)  # this is requested twice, but cached
    lenders = credibilty(client, me, them)
    percent = len(lenders) / len(thier_followers)
    return percent


def credibilty(
    client: atproto.Client, me: str, them: str
) -> typing.Dict[str, typing.Any]:
    """
    For some person I follow,
    show who lends 'credibility' to them in the form of a follow
    """
    my_following = get_following(client, me)
    thier_followers = get_followers(client, them)
    lenders = {k: v for k, v in my_following.items() if k in thier_followers}
    return lenders


def get_profile(client: atproto.Client, handle: str) -> typing.Dict[str, typing.Any]:
    profile: atproto.models.AppBskyActorDefs.ProfileViewDetailed = _get_or_return_cache(
        handle, "get_profile", lambda: _get_profile(client, handle)
    )
    return {profile.did: _format_detailed_profile(profile)}


def get_followers(client: atproto.Client, handle: str) -> typing.Dict[str, typing.Any]:
    followers = {
        profile.did: _format_profile(profile)
        for profile in _get_or_return_cache(
            handle, "get_followers", lambda: _get_followers(client, handle)
        )
    }
    return followers


def get_following(client: atproto.Client, handle: str) -> typing.Dict[str, typing.Any]:
    followers = {
        profile.did: _format_profile(profile)
        for profile in _get_or_return_cache(
            handle, "get_following", lambda: _get_following(client, handle)
        )
    }
    return followers


def get_following_handles(client: atproto.Client, handle: str) -> list[str]:
    return _get_or_return_cache(
        handle,
        "get_following_handles",
        lambda: [profile.handle for profile in _get_following(client, handle)],
    )


def _format_detailed_profile(
    profile: atproto.models.AppBskyActorDefs.ProfileViewDetailed,
) -> dict[str, typing.Any]:
    return {
        "did": profile.did,
        "handle": profile.handle,
        "avatar": profile.avatar,
        "description": profile.description,
        "displayName": profile.display_name,
        "followersCount": profile.followers_count,
        "followsCount": profile.follows_count,
    }


def _format_profile(
    profile: atproto.models.AppBskyActorDefs.ProfileView,
) -> dict[str, typing.Any]:
    return {
        "did": profile.did,
        "handle": profile.handle,
        "avatar": profile.avatar,
        "description": profile.description,
        "displayName": profile.display_name,
    }


#########################
# CODE FORMATTING RULES #
#########################

# Every function past this point should:
#   1. be doing something that takes a nontrivial amount of time (like making a network request)
#   2. start a span, with its function inputs as attributes.
#   3. should be cached inside of the functions calling them (except the cache itself, obviously)


def _get_or_return_cache(
    suffix: str, func_name: str, func: typing.Callable
) -> typing.Any:
    key = f"{func_name}-{suffix}"
    with telemetry.tracer.start_as_current_span("_get_or_return_cache") as span:
        span.set_attribute("key", key)
        span.set_attribute("func_name", func_name)
        span.set_attribute("suffix", suffix)

        if key in cache:
            span.set_attribute("adjective", "hit")
            logger.info("cache", adjective="hit", func_name=func_name, key=key)
            return cache[key]
        else:
            span.set_attribute("adjective", "miss")
            logger.info("cache", adjective="miss", func_name=func_name, key=key)
            result = func()
            cache[key] = result
            return result


def _get_profile(
    client: atproto.Client,
    handle: str,
) -> atproto.models.AppBskyActorDefs.ProfileViewDetailed:
    with telemetry.tracer.start_as_current_span("_get_profile") as span:
        span.set_attribute("handle", handle)

        # https://docs.bsky.app/docs/api/app-bsky-actor-get-profile
        response: atproto.models.AppBskyActorDefs.ProfileViewDetailed = (
            client.get_profile(handle)
        )
        return response


def _get_followers(
    client: atproto.Client,
    handle: str,
    cursor: str = "",
    followers: typing.Optional[
        list[atproto.models.AppBskyActorDefs.ProfileView]
    ] = None,
    depth: int = 0,
) -> list[atproto.models.AppBskyActorDefs.ProfileView]:
    with telemetry.tracer.start_as_current_span("_get_followers") as span:
        span.set_attribute("handle", handle)
        span.set_attribute("depth", depth)
        span.set_attribute("followers", len(followers) if followers else 0)

        # https://docs.bsky.app/docs/api/app-bsky-graph-get-followers
        followers = followers or []
        response: atproto.models.AppBskyGraphGetFollowers.Response = (
            client.get_followers(handle, limit=100, cursor=cursor)
        )
        followers = followers + response.followers
        depth += 1
        if response.cursor and depth < MAX_FOLLOWS_PAGES:
            return _get_followers(
                client, handle, cursor=response.cursor, followers=followers, depth=depth
            )
        else:
            return followers or []


def _get_following(
    client: atproto.Client,
    handle: str,
    cursor: str = "",
    following: typing.Optional[
        list[atproto.models.AppBskyActorDefs.ProfileView]
    ] = None,
    depth: int = 0,
) -> list[atproto.models.AppBskyActorDefs.ProfileView]:
    with telemetry.tracer.start_as_current_span("_get_following") as span:
        span.set_attribute("handle", handle)
        span.set_attribute("depth", depth)
        span.set_attribute("following", len(following) if following else 0)

        # https://docs.bsky.app/docs/api/app-bsky-graph-get-follows
        following = following or []
        response: atproto.models.AppBskyGraphGetFollows.Response = client.get_follows(
            handle, limit=100, cursor=cursor
        )
        following = following + response.follows
        depth += 1
        if response.cursor and depth < MAX_FOLLOWS_PAGES:
            return _get_following(
                client, handle, cursor=response.cursor, following=following, depth=depth
            )
        else:
            return following or []
