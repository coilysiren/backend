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


async def credibilty_percent(client: atproto.Client, me: str, them: str) -> float:
    """
    For some person I follow,
    show who lends 'credibility' to them in the form of a follow,
    as of of a percent of their followers.
    1 (eg. 100%) credibility would mean that all of their followers are people I follow.
    """
    thier_followers = await get_followers(client, them)  # this is requested twice, but cached
    lenders = await credibilty(client, me, them)
    percent = len(lenders) / len(thier_followers)
    return percent


async def credibilty(client: atproto.Client, me: str, them: str) -> typing.Dict[str, typing.Any]:
    """
    For some person I follow,
    show who lends 'credibility' to them in the form of a follow
    """
    my_following = await get_following(client, me)
    thier_followers = await get_followers(client, them)
    lenders = {k: v for k, v in my_following.items() if k in thier_followers}
    return lenders


async def get_profile(client: atproto.Client, handle: str) -> typing.Dict[str, typing.Any]:
    profile: atproto.models.AppBskyActorDefs.ProfileViewDetailed = await cache.get_or_return_cached(
        "bsky.get-profile", handle, lambda: _get_profile(client, handle)
    )
    return {profile["did"]: profile}


async def get_followers(client: atproto.Client, handle: str) -> typing.Dict[str, typing.Any]:
    follows = {
        profile["did"]: profile
        for profile in await cache.get_or_return_cached(
            "bsky.get-followers", handle, lambda: _get_followers(client, handle)
        )
    }
    return follows


async def get_following(client: atproto.Client, handle: str) -> typing.Dict[str, typing.Any]:
    follows = {
        profile["did"]: profile
        for profile in await cache.get_or_return_cached(
            "bsky.get-following", handle, lambda: _get_following(client, handle)
        )
    }
    return follows


async def get_following_handles(client: atproto.Client, handle: str) -> list[str]:
    output = await cache.get_or_return_cached(
        "bsky.get-following-handles",
        handle,
        lambda: _get_following_handles(client, handle),
    )
    return output


async def get_author_feed(
    client: atproto.Client, handle: str, cursor: str = ""
) -> tuple[list[dict[str, typing.Any]], str]:
    return await cache.get_or_return_cached(
        f"bsky.get-author-feed-{cursor}",
        handle,
        lambda: _get_author_feed(client, handle, cursor),
    )


async def get_author_feed_text(client: atproto.Client, handle: str, cursor: str = "") -> tuple[list[str], str]:
    """
    Get the text of the author's feed.
    """
    return await cache.get_or_return_cached(
        f"bsky.get-author-feed-text-{cursor}",
        handle,
        lambda: _get_author_feed_text(client, handle, cursor),
    )


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


def _filter_profiles(
    profiles: list[atproto.models.AppBskyActorDefs.ProfileViewBasic],
) -> list[atproto.models.AppBskyActorDefs.ProfileViewBasic]:
    """
    Filter out any profiles that are invalid, or blocked (in either direction).
    """
    return [
        profile
        for profile in profiles
        if not (
            profile.handle == "handle.invalid"
            or (
                profile.viewer
                and (
                    profile.viewer.blocking is True
                    or profile.viewer.blocked_by is True
                    or profile.viewer.blocking_by_list is True
                )
            )
        )
    ]


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
        "viewerBlocking": profile.viewer.blocking if profile.viewer else None,
        "viewerBlockedBy": profile.viewer.blocked_by if profile.viewer else None,
        "viewerBlockingByList": profile.viewer.blocking_by_list if profile.viewer else None,
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
        "viewerBlocking": profile.viewer.blocking if profile.viewer else None,
        "viewerBlockedBy": profile.viewer.blocked_by if profile.viewer else None,
        "viewerBlockingByList": profile.viewer.blocking_by_list if profile.viewer else None,
        "description": profile.description,  # The only thing that's different from the basic profile
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
        "viewerBlocking": profile.viewer.blocking if profile.viewer else None,
        "viewerBlockedBy": profile.viewer.blocked_by if profile.viewer else None,
        "viewerBlockingByList": profile.viewer.blocking_by_list if profile.viewer else None,
    }


def _format_feed_view(
    post: atproto.models.AppBskyFeedDefs.FeedViewPost,
) -> dict[str, typing.Any]:
    return {
        "reasonBy": _format_profile_basic(post.reason.by) if post.reason else None,
        "feedContext": post.feed_context,
        #
        **_format_post(
            "post",
            post.post,
        ),
        **_format_post(
            "post",
            (
                post.reply.root
                if post.reply and post.reply.root and not getattr(post.reply.root, "not_found", True)
                else None
            ),
        ),
        **_format_post(
            "post",
            (
                post.reply.parent
                if post.reply and post.reply.parent and not getattr(post.reply.parent, "not_found", True)
                else None
            ),
        ),
        "replyGrandparent": (
            _format_profile_basic(post.reply.grandparent_author)
            if post.reply and post.reply and post.reply.grandparent_author
            else None
        ),
    }


def _format_post(
    prefix: str,
    post: atproto.models.AppBskyFeedDefs.PostView | None,
) -> dict[str, typing.Any]:
    return (
        {
            f"{prefix}Author": _format_profile_basic(post.author),
            f"{prefix}Text": post.record.text,
            f"{prefix}Cid": post.cid,
            f"{prefix}Uri": post.uri,
            f"{prefix}LikeCount": post.like_count,
            f"{prefix}RepostCount": post.repost_count,
            f"{prefix}QuoteCount": post.quote_count,
            f"{prefix}ReplyCount": post.reply_count,
            f"{prefix}ViewerLike": post.viewer.like,
            f"{prefix}ViewerRepost": post.viewer.repost,
        }
        if post
        else {}
    )


#########################
# CODE FORMATTING RULES #
#########################

# Every function past this point should:
#   1. be doing something that takes a nontrivial amount of time (like making a network request)
#   2. start a span, with its function inputs as attributes.
#   3. should be cached inside of the functions calling them (except the cache itself, obviously)


def _get_author_feed_text(
    client: atproto.Client,
    handle: str,
    cursor: str = "",
) -> tuple[list[str], str]:
    with _telemetry.tracer.start_as_current_span("bsky.get-author-feed-text") as span:
        span.set_attribute("handle", handle)
        # https://docs.bsky.app/docs/api/app-bsky-feed-get-author-feed

        response: atproto.models.AppBskyFeedGetAuthorFeed.Response = client.get_author_feed(
            handle,
            limit=100,
            cursor=cursor,
        )
        return ([post.post.record.text for post in response.feed], response.cursor)


def _get_author_feed(
    client: atproto.Client,
    handle: str,
    cursor: str = "",
) -> tuple[list[dict[str, typing.Any]], str]:
    with _telemetry.tracer.start_as_current_span("bsky.get-author-feed") as span:
        span.set_attribute("handle", handle)
        # https://docs.bsky.app/docs/api/app-bsky-feed-get-author-feed

        response: atproto.models.AppBskyFeedGetAuthorFeed.Response = client.get_author_feed(
            handle,
            limit=100,
            cursor=cursor,
        )
        print("response", response)
        return ([_format_feed_view(feed_view) for feed_view in response.feed], response.cursor)


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
    followers: typing.Optional[list[dict[str, typing.Any]]] = None,
    depth: int = 0,
) -> list[dict[str, typing.Any]]:
    with _telemetry.tracer.start_as_current_span("bsky.get-followers") as span:
        span.set_attribute("handle", handle)
        span.set_attribute("followers", len(followers) if followers else 0)

        # https://docs.bsky.app/docs/api/app-bsky-graph-get-followers
        followers = followers or []
        response: atproto.models.AppBskyGraphGetFollowers.Response = client.get_followers(
            handle, limit=100, cursor=cursor
        )
        followers = followers + [_format_profile(profile) for profile in _filter_profiles(response.followers)]
        depth += 1
        if response.cursor and depth < MAX_FOLLOWS_PAGES:
            return _get_followers(client, handle, cursor=response.cursor, followers=followers, depth=depth)
        else:
            return followers or []


def _get_following(
    client: atproto.Client,
    handle: str,
    cursor: str = "",
    following: typing.Optional[list[dict[str, typing.Any]]] = None,
    depth: int = 0,
) -> list[dict[str, typing.Any]]:
    with _telemetry.tracer.start_as_current_span("bsky.get-following") as span:
        span.set_attribute("handle", handle)
        span.set_attribute("following", len(following) if following else 0)

        # https://docs.bsky.app/docs/api/app-bsky-graph-get-follows
        following = following or []
        response: atproto.models.AppBskyGraphGetFollows.Response = client.get_follows(handle, limit=100, cursor=cursor)
        following = following + [_format_profile(profile) for profile in _filter_profiles(response.follows)]
        depth += 1
        if response.cursor and depth < MAX_FOLLOWS_PAGES:
            return _get_following(client, handle, cursor=response.cursor, following=following, depth=depth)
        else:
            return following or []


def _get_following_handles(
    client: atproto.Client,
    handle: str,
    cursor: str = "",
    handles: typing.Optional[list[str]] = None,
    depth: int = 0,
) -> list[str]:
    with _telemetry.tracer.start_as_current_span("bsky.get-following") as span:
        span.set_attribute("handle", handle)
        span.set_attribute("following", len(handles) if handles else 0)

        # https://docs.bsky.app/docs/api/app-bsky-graph-get-follows
        handles = handles or []
        response: atproto.models.AppBskyGraphGetFollows.Response = client.get_follows(handle, limit=100, cursor=cursor)
        handles = handles + [profile.handle for profile in _filter_profiles(response.follows)]
        depth += 1
        if response.cursor and depth < MAX_FOLLOWS_PAGES:
            return _get_following_handles(client, handle, cursor=response.cursor, handles=handles, depth=depth)
        else:
            return handles or []
