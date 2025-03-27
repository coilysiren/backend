import os
import typing

import atproto  # type: ignore
import structlog


log = structlog.get_logger()
cache: typing.Dict[str, typing.Any] = {}
FOLLOWS_PER_PAGE = 100  # the max
MAX_FOLLOWS_PAGES = 50  # this number * FOLLOWS_PER_PAGE is the max number of follows to list


def init():
    client = atproto.Client("https://bsky.social")
    client.login(login=os.getenv("BSKY_USERNAME"), password=os.getenv("BSKY_PASSWORD"))
    return client


def recommendations(client: atproto.Client, me: str) -> list[str]:
    """
    For everyone that I follow,
    list who they follow that I don't follow.
    """
    my_following = get_following_handles(client, me)
    reccomendations = []

    # For everyone that I follow,
    for my_follow in my_following:

        # List of who they follow
        following = get_following_handles(client, my_follow)

        # And remove the people I follow
        for thier_follow in following:
            if thier_follow not in my_following:

                # Then add them to the reccomendations
                reccomendations.append(thier_follow)

    return reccomendations


def credibilty_percent(client: atproto.Client, me: str, them: str) -> float:
    """
    For some person I follow,
    show who lends 'credibility' to them in the form of a follow,
    as of of a percent of their followers.
    100% credibility would mean that all of their followers are people I follow.
    """
    thier_followers = get_followers(client, them)  # this is requested twice, but cached
    lenders = credibilty(client, me, them)
    percent = len(lenders) / len(thier_followers)
    return round(percent * 100, 0)


def credibilty(client: atproto.Client, me: str, them: str) -> typing.Dict[str, typing.Any]:
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
        handle, "get_profile", lambda: client.get_profile(handle)
    )
    return {
        profile.did: {
            "handle": profile.handle,
            "avatar": profile.avatar,
            "description": profile.description,
            "display_name": profile.display_name,
            "followers_count": profile.followers_count,
            "follows_count": profile.follows_count,
            "created_at": profile.created_at,
        }
    }


def get_followers(client: atproto.Client, handle: str) -> typing.Dict[str, typing.Any]:
    followers = {
        profile.did: _format_profile(profile)
        for profile in _get_or_return_cache(handle, "get_followers", lambda: _get_followers(client, handle))
    }
    return followers


def get_following(client: atproto.Client, handle: str) -> typing.Dict[str, typing.Any]:
    followers = {
        profile.did: _format_profile(profile)
        for profile in _get_or_return_cache(handle, "get_following", lambda: _get_following(client, handle))
    }
    return followers


def get_following_handles(client: atproto.Client, handle: str) -> list[str]:
    return _get_or_return_cache(
        handle, "get_following_handles", lambda: [profile.handle for profile in _get_following(client, handle)]
    )


def _format_profile(profile: atproto.models.AppBskyActorDefs.ProfileView) -> dict[str, typing.Any]:
    return {
        "handle": profile.handle,
        "avatar": profile.avatar,
        "description": profile.description,
        "display_name": profile.display_name,
    }


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


def _get_followers(
    client: atproto.Client,
    handle: str,
    cursor: str = "",
    followers: typing.Optional[list[atproto.models.AppBskyActorDefs.ProfileView]] = None,
    depth: int = 0,
) -> list[atproto.models.AppBskyActorDefs.ProfileView]:
    followers = followers or []

    # https://docs.bsky.app/docs/api/app-bsky-graph-get-followers
    response: atproto.models.AppBskyGraphGetFollowers.Response = client.get_followers(handle, limit=100, cursor=cursor)
    followers = followers + response.followers
    depth += 1
    if response.cursor and depth < MAX_FOLLOWS_PAGES:
        return _get_followers(client, handle, cursor=response.cursor, followers=followers, depth=depth)
    else:
        return followers or []


def _get_following(
    client: atproto.Client,
    handle: str,
    cursor: str = "",
    following: typing.Optional[list[atproto.models.AppBskyActorDefs.ProfileView]] = None,
    depth: int = 0,
) -> list[atproto.models.AppBskyActorDefs.ProfileView]:
    following = following or []

    # https://docs.bsky.app/docs/api/app-bsky-graph-get-follows
    response: atproto.models.AppBskyGraphGetFollows.Response = client.get_follows(handle, limit=100, cursor=cursor)
    following = following + response.follows
    depth += 1
    if response.cursor and depth < MAX_FOLLOWS_PAGES:
        return _get_following(client, handle, cursor=response.cursor, following=following, depth=depth)
    else:
        return following or []
