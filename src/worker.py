import atproto  # type: ignore

from . import bsky
from . import cache
from . import data_science


async def process_emoji_summary(
    bsky_client: atproto.Client, task_id: str, handle: str, num_keywords: int, num_feed_pages: int
) -> list[tuple[str, str, str]]:
    """
    Process the emoji summary in the background.
    Updates cache with progress and results.
    """
    try:
        data_science_client = data_science.DataScienceClient()

        # Get the author's feed texts
        text_lines = await bsky.get_author_feed_texts(bsky_client, handle, num_feed_pages)
        text_joined = "\n".join(text_lines)

        # Get the keywords and emoji match scores
        keywords = data_science.extract_keywords(data_science_client, handle, text_joined, num_keywords)
        emoji_match_scores = data_science.get_emoji_match_scores(data_science_client, handle, keywords)
        emoji_descriptions = data_science.join_description_and_emoji_score(text_lines, emoji_match_scores)

        # Store results in cache
        cache.set_async_task_data(
            "emoji-summary",
            handle,
            cache.AsyncTaskData(
                task_id=task_id,
                task_status=cache.TaskDataStatus.completed,
                task_data=emoji_descriptions,
            ),
        )

        return emoji_descriptions

    except Exception as exc:
        cache.set_async_task_data(
            "emoji-summary",
            handle,
            cache.AsyncTaskData(
                task_id=task_id,
                task_status=cache.TaskDataStatus.failed,
                task_data=str(exc),
            ),
        )

    return []
