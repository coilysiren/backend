import os

import typing

import atproto


def init():
    client = atproto.Client("https://bsky.social")
    client.login(login="coilysiren.me", password=os.getenv("BSKY_PASSWORD"))
    return client


def get_followers(client: atproto.Client, handle: str) -> typing.Dict[str, typing.Any]:
    followers = {profile.did: _format_profile(profile) for profile in _get_followers(client, handle)}
    return followers


def get_following(client: atproto.Client, handle: str) -> typing.Dict[str, typing.Any]:
    followers = {profile.did: _format_profile(profile) for profile in _get_following(client, handle)}
    return followers


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
