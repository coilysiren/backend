import os
import re
import typing

import atproto  # type: ignore
import structlog

from . import cache, telemetry

_telemetry = telemetry.Telemetry()
logger = structlog.get_logger()

# MAX_FOLLOWS_PAGES * FOLLOWS_PER_PAGE is the max number of follows to list
FOLLOWS_PER_PAGE = 100  # the max
MAX_FOLLOWS_PAGES = 25

SUGGESTIONS_PER_PAGE = 10
MAX_SUGGESTION_PAGES = 10

POPULARITY_PER_PAGE = 50
MAX_POPULARITY_PAGES = 50


def init():
    client = atproto.Client("https://bsky.social")
    client.login(login=os.getenv("BSKY_USERNAME"), password=os.getenv("BSKY_PASSWORD"))
    return client


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


def popularity(client: atproto.Client, me: str, index=0) -> tuple[dict[str, int], int]:
    """
    For every person I follow,
    list people who they follow,
    and aggregate that list to see how popular each person is.
    """
    next_index = index + POPULARITY_PER_PAGE
    my_following = get_following_handles(client, me)
    my_following.sort()
    my_following_to_check = my_following[index:next_index]

    popularity_dict: dict[str, int] = {}

    # For everyone that I follow,
    for my_follow in my_following_to_check:

        # List of who they follow
        following = get_following_handles(client, my_follow)

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


def suggestions(client: atproto.Client, me: str, index=0) -> tuple[list[str], int]:
    """
    For everyone that I follow,
    list who they follow that I don't follow.
    """
    next_index = index + SUGGESTIONS_PER_PAGE
    my_following = get_following_handles(client, me)
    my_following.sort()
    my_following_to_check = my_following[index:next_index]

    suggestions = []

    # For everyone that I follow,
    for my_follow in my_following_to_check:

        # List of who they follow
        following = get_following_handles(client, my_follow)

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
    profile: atproto.models.AppBskyActorDefs.ProfileViewDetailed = cache.get_or_return_cached(
        "bsky.get-profile", handle, lambda: _get_profile(client, handle)
    )
    return {profile["did"]: profile}


def get_followers(client: atproto.Client, handle: str) -> typing.Dict[str, typing.Any]:
    followers = {
        profile.did: _format_profile(profile)
        for profile in cache.get_or_return_cached("bsky.get-followers", handle, lambda: _get_followers(client, handle))
    }
    return followers


def get_following(client: atproto.Client, handle: str) -> typing.Dict[str, typing.Any]:
    followers = {
        profile.did: _format_profile(profile)
        for profile in cache.get_or_return_cached("bsky.get-following", handle, lambda: _get_following(client, handle))
    }
    return followers


def get_following_handles(client: atproto.Client, handle: str) -> list[str]:
    return cache.get_or_return_cached(
        "bsky.get-following-handles",
        handle,
        lambda: [profile.handle for profile in _get_following(client, handle)],
    )


def _format_detailed_profile(
    profile: atproto.models.AppBskyActorDefs.ProfileViewDetailed,
) -> dict[str, typing.Any]:
    return {
        "did": profile.did,
        "handle": profile.handle,
        "avatar": profile.avatar,
        "banner": profile.banner,
        "created_at": profile.created_at,
        "description": profile.description,
        "displayName": profile.display_name,
        "followersCount": profile.followers_count,
        "followsCount": profile.follows_count,
        "postCount": profile.posts_count,
        "pinnedPostCid": profile.pinned_post.cid if profile.pinned_post else None,
        "pinnedPostUri": profile.pinned_post.uri if profile.pinned_post else None,
        "viewerFollowedBy": profile.viewer.followed_by if profile.viewer else None,
        "viewerFollowing": profile.viewer.following if profile.viewer else None,
        "viewerKnownFollowersCount": (
            profile.viewer.known_followers.count if profile.viewer and profile.viewer.known_followers else 0
        ),
        "viewerKnownFollowers": (
            [_format_profile_basic(follower) for follower in profile.viewer.known_followers.followers]
            if profile.viewer and profile.viewer.known_followers
            else []
        ),
    }


def _format_profile(
    profile: atproto.models.AppBskyActorDefs.ProfileView,
) -> dict[str, typing.Any]:
    return {
        "did": profile.did,
        "handle": profile.handle,
        "avatar": profile.avatar,
        "displayName": profile.display_name,
        "createdAt": profile.created_at,
        "description": profile.description,
    }


def _format_profile_basic(
    profile: atproto.models.AppBskyActorDefs.ProfileViewBasic,
) -> dict[str, typing.Any]:
    return {
        "did": profile.did,
        "handle": profile.handle,
        "avatar": profile.avatar,
        "displayName": profile.display_name,
        "createdAt": profile.created_at,
    }


#########################
# CODE FORMATTING RULES #
#########################

# Every function past this point should:
#   1. be doing something that takes a nontrivial amount of time (like making a network request)
#   2. start a span, with its function inputs as attributes.
#   3. should be cached inside of the functions calling them (except the cache itself, obviously)


def _get_profile(
    client: atproto.Client,
    handle: str,
) -> dict[str, typing.Any]:
    with _telemetry.tracer.start_as_current_span("bsky.get-profile") as span:
        span.set_attribute("handle", handle)

        # https://docs.bsky.app/docs/api/app-bsky-actor-get-profile
        response: atproto.models.AppBskyActorDefs.ProfileViewDetailed = client.get_profile(handle)
        output = _format_detailed_profile(response)
        return output


def _get_followers(
    client: atproto.Client,
    handle: str,
    cursor: str = "",
    followers: typing.Optional[list[atproto.models.AppBskyActorDefs.ProfileView]] = None,
    depth: int = 0,
) -> list[atproto.models.AppBskyActorDefs.ProfileView]:
    with _telemetry.tracer.start_as_current_span("bsky.get-followers") as span:
        span.set_attribute("handle", handle)
        span.set_attribute("depth", depth)
        span.set_attribute("followers", len(followers) if followers else 0)

        # https://docs.bsky.app/docs/api/app-bsky-graph-get-followers
        followers = followers or []
        response: atproto.models.AppBskyGraphGetFollowers.Response = client.get_followers(
            handle, limit=100, cursor=cursor
        )
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
    with _telemetry.tracer.start_as_current_span("bsky.get-following") as span:
        span.set_attribute("handle", handle)
        span.set_attribute("depth", depth)
        span.set_attribute("following", len(following) if following else 0)

        # https://docs.bsky.app/docs/api/app-bsky-graph-get-follows
        following = following or []
        response: atproto.models.AppBskyGraphGetFollows.Response = client.get_follows(handle, limit=100, cursor=cursor)
        following = following + response.follows
        depth += 1
        if response.cursor and depth < MAX_FOLLOWS_PAGES:
            return _get_following(client, handle, cursor=response.cursor, following=following, depth=depth)
        else:
            return following or []
