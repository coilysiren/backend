import dataclasses
import json
import os
import subprocess
import typing
import asyncio

import nltk  # type: ignore
import nltk.corpus  # type: ignore
import numpy
import spacy
import spacy.language
import spacy.tokens.doc as spacy_doc
import structlog
import yake  # type: ignore
import yaml  # type: ignore

logger = structlog.get_logger()


@dataclasses.dataclass
class EmojiData(object):
    emoji: str
    description: str
    nlp: spacy_doc.Doc


@dataclasses.dataclass
class KeywordData(object):
    score: numpy.float64
    keyword: str


@dataclasses.dataclass
class KeywordEmojiData(object):
    keyword: str
    score: float
    emoji: str


class DataScienceClient(object):
    _instance: typing.Optional["DataScienceClient"] = None
    _initialized: bool = False
    emojis = [EmojiData]
    ignore_list: set[str] = set()
    nlp: spacy.language.Language

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataScienceClient, cls).__new__(cls)
        return cls._instance

    async def initialize(self):
        if not self._initialized:
            await asyncio.to_thread(self._load_nltk)
            self.nlp = await asyncio.to_thread(self._load_nlp)
            self.emojis = await asyncio.to_thread(self._load_emojis)
            self.ignore_list = await asyncio.to_thread(self._load_ignore_list)
            self._initialized = True

    def _load_nltk(self):
        nltk.download("stopwords")

    def _load_nlp(self):
        subprocess.run(["spacy", "download", "en_core_web_lg"], check=True)
        return spacy.load("en_core_web_lg")

    def _load_emojis(self):
        with open(os.path.join("emojis.json"), "r", encoding="utf-8") as _file:
            emojis = json.loads(_file.read())

        return [
            EmojiData(
                emojis[emoji_index]["emoji"],
                emojis[emoji_index]["description"],
                self.nlp(emojis[emoji_index]["description"]),
            )
            for emoji_index in range(len(emojis))
        ]

    def _load_ignore_list(self):
        with open("nlp_ignore.yml", "r", encoding="utf-8") as _file:
            ignore_list = yaml.load(_file, yaml.Loader)

        return set(nltk.corpus.stopwords.words("english") + list(self.nlp.Defaults.stop_words) + ignore_list)


def _remove_substring_entries(keywords: list[KeywordData]) -> list[KeywordData]:
    """
    Given a list of keywords, remove any keywords that are substrings of other keywords.
    For example, if the list contains "cat" and "cat food", remove "cat".
    """
    # Sort by length of keyword (longest first)
    keywords.sort(key=lambda x: (-len(x.keyword), x.keyword))

    filtered_keywords = []
    seen_words = set()

    # As you go down the list (longest first), add to a list of words you have seen so far.
    # If you see a word that is not in the list, add it to the list.
    # If you see a word that is in the list, skip it.
    for keyword_data in keywords:
        words = set(keyword_data.keyword.split())
        if not any(word in seen_words for word in words):
            filtered_keywords.append(keyword_data)
            seen_words.update(words)

    return filtered_keywords


def extract_keywords(client: DataScienceClient, handle: str, text: str, num_keywords: int = 50) -> list[KeywordData]:
    """
    Given a `client` that contains a simple ignore list.
    And a `text` input to extract keywords from.
    Return a list of keywords.
    """

    # https://pypi.org/project/yake/
    yake_kw_extractor = yake.KeywordExtractor(
        lan="en",
        top=num_keywords,
        dedupLim=1,
        stopwords=client.ignore_list,
    )
    keywords = yake_kw_extractor.extract_keywords(text.lower())

    # This block is necessary because the order of the tuples is not consistent.
    # Sometimes it's (keyword, score), sometimes it's (score, keyword).
    # This depends on the operating system, as far as I can tell.
    keywords = [
        KeywordData(pair[1], pair[0]) if isinstance(pair[0], str) else KeywordData(pair[0], pair[1])
        for pair in keywords
    ]

    # Sometimes the stopwords are not removed.
    # So we need to remove them manually.
    keywords = [keyword for keyword in keywords if keyword.keyword not in client.ignore_list]

    keywords = _remove_substring_entries(keywords)
    logger.info(
        "extract-keywords",
        handle=handle,
        **{keyword.keyword.replace(" ", "-"): float(keyword.score) for keyword in keywords},
    )
    return keywords


def get_emoji_match_scores(
    client: DataScienceClient,
    handle: str,
    keywords: list[KeywordData],
    num_matches: int = 10,
) -> list[KeywordEmojiData]:
    """
    Give a `client` that contains a list of emojis.
    And a set of `keywords` to match against the emojis.
    Get the "best of the best" matches of emojis to keywords.
    """

    emoji_match_scores: list[KeywordEmojiData] = []

    for keyword_data in keywords:
        _keyword: spacy_doc.Doc = client.nlp(keyword_data.keyword)
        keyword_scores: list[KeywordEmojiData] = []

        # Check each keyword against each emoji
        for emoji_index in range(len(client.emojis)):

            # Check if emoji is in keyword or vice versa
            if any(
                word == client.emojis[emoji_index].description.lower() for word in keyword_data.keyword.lower().split()
            ) or any(
                word == keyword_data.keyword.lower() for word in client.emojis[emoji_index].description.lower().split()
            ):
                # If so, then set to the max similarity score
                emoji_match_score = 1.0
            else:
                # Otherwise, use semantic similarity
                # https://spacy.io/api/doc#similarity
                emoji_match_score = _keyword.similarity(client.emojis[emoji_index].nlp)

            keyword_scores.append(
                KeywordEmojiData(
                    str(_keyword),
                    emoji_match_score,
                    client.emojis[emoji_index].emoji,
                )
            )

        # Sort emoji matches by highest similarity.
        # and append best match to emoji_match_scores.
        # Where "best" means "the most similar to the keyword".
        keyword_scores.sort(key=lambda x: -x.score)
        emoji_match_scores.append(keyword_scores[0])

    # Sort overall results by highest similarity, and clip them
    # This results in a list of the best matches for each keyword.
    # This is intentionally the same sort + clip as above, but on the whole list.
    # This produces a "best of the best" list.
    emoji_match_scores.sort(key=lambda x: -x.score)
    emoji_match_scores = emoji_match_scores[:num_matches]
    logger.info(
        "emoji-match-scores",
        handle=handle,
        **{
            emoji_match_score.keyword.replace(" ", "-"): float(emoji_match_score.score)
            for emoji_match_score in emoji_match_scores
        },
    )
    return emoji_match_scores


def join_description_and_emoji_score(text_lines: list[str], emoji_match_scores: list[KeywordEmojiData]):
    emoji_descriptions = []

    for emoji_score in emoji_match_scores:
        for quote in text_lines:
            if str(emoji_score.keyword) in quote:
                emoji_descriptions.append(
                    [
                        emoji_score.emoji,
                        emoji_score.keyword,
                        quote,
                    ]
                )
                break
    return emoji_descriptions
