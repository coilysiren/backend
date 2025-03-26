import os
import typing

import atproto  # type: ignore
import structlog


log = structlog.get_logger()
cache: typing.Dict[str, typing.Any] = {}


def init():
    client = atproto.Client("https://bsky.social")
    client.login(login=os.getenv("BSKY_USERNAME"), password=os.getenv("BSKY_PASSWORD"))
    return client


def get_followers(client: atproto.Client, handle: str, did: str) -> typing.Dict[str, typing.Any]:
    followers = {
        profile.did: _format_profile(profile)
        for profile in _get_or_return_cache(f"{did}", "get_followers", lambda: _get_followers(client, handle))
    }
    return followers


def get_following(client: atproto.Client, handle: str, did: str) -> typing.Dict[str, typing.Any]:
    followers = {
        profile.did: _format_profile(profile)
        for profile in _get_or_return_cache(f"{did}", "get_following", lambda: _get_following(client, handle))
    }
    return followers


def _get_or_return_cache(key: str, func_name: str, func: typing.Callable) -> typing.Any:
    key = f"{func_name}-{key}"
    if key in cache:
        log.info("cache", adjective="hit", func_name=func_name, key=key)
        return cache[key]
    else:
        log.info("cache", adjective="miss", func_name=func_name, key=key)
        result = func()
        cache[key] = result
        return result


def _format_profile(profile: atproto.models.AppBskyActorDefs.ProfileView) -> dict[str, typing.Any]:
    return {
        "handle": profile.handle,
        "avatar": profile.avatar,
        "description": profile.description,
        "display_name": profile.display_name,
    }


def _get_followers(
    client: atproto.Client,
    handle: str,
    cursor: str = "",
    followers: typing.Optional[list[atproto.models.AppBskyActorDefs.ProfileView]] = None,
) -> list[atproto.models.AppBskyActorDefs.ProfileView]:
    followers = followers or []

    response: atproto.models.AppBskyGraphGetFollowers.Response = client.get_followers(handle, limit=100, cursor=cursor)
    followers = followers + response.followers
    if response.cursor:
        return _get_followers(client, handle, cursor=response.cursor, followers=followers)
    else:
        return followers or []


def _get_following(
    client: atproto.Client,
    handle: str,
    cursor: str = "",
    following: typing.Optional[list[atproto.models.AppBskyActorDefs.ProfileView]] = None,
) -> list[atproto.models.AppBskyActorDefs.ProfileView]:
    following = following or []

    response: atproto.models.AppBskyGraphGetFollows.Response = client.get_follows(handle, limit=100, cursor=cursor)
    following = following + response.follows
    if response.cursor:
        return _get_following(client, handle, cursor=response.cursor, following=following)
    else:
        return following or []
