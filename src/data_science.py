import os
import nltk
import nltk.corpus
import subprocess
import spacy
import yake
import nltk
import nltk.corpus
import spacy
import yaml
import pprint
import spacy
import json
import spacy.language
import spacy.tokens.doc as spacy_doc


class DataScienceClient(object):

    initalized = False
    emojis = []
    emoji_nlp = []
    ignore_list = set()
    nlp: spacy.language.Language = None

    def __new__(cls):
        if not cls.initalized:
            cls._load_nltk(cls)
            cls.nlp = cls._load_nlp(cls)
            cls.emojis = cls._load_emojis(cls)
            cls.emoji_nlp = cls._load_emoji_nlp(cls)
            cls.ignore_list = cls._load_ignore_list(cls)
            cls.initalized = True
        return cls

    def _load_nltk(self):
        nltk.download("stopwords")

    def _load_nlp(self):
        # TODO: only run once on a machine
        # subprocess.run(["spacy", "download", "en_core_web_lg"])
        return spacy.load("en_core_web_lg")

    def _load_emojis(self):
        with open(os.path.join("emojis.json"), "r", encoding="utf-8") as _file:
            emojis = json.loads(_file.read())

        return emojis

    def _load_emoji_nlp(self):
        emoji_nlp = [
            self.nlp(self.emojis[emoji_index]["description"])
            for emoji_index in range(len(self.emojis))
        ]

        return emoji_nlp

    def _load_ignore_list(self):
        with open("nlp_ignore.yml", "r", encoding="utf-8") as _file:
            ignore_list = yaml.load(_file, yaml.Loader)

        return set(
            nltk.corpus.stopwords.words("english")
            + list(self.nlp.Defaults.stop_words)
            + ignore_list
        )


def _remove_substring_entries(keyword_list: list[tuple[int, str]]):
    # Sort by length of keyword (longest first), then by score (higher is better)
    keyword_list.sort(key=lambda x: (-x[0], -len(x[1])))

    filtered_keywords = []
    seen_words = set()

    for score, keyword in keyword_list:
        words = set(keyword.split())  # Split phrase into individual words
        if not any(word in seen_words for word in words):
            filtered_keywords.append((score, keyword))
            seen_words.update(words)  # Add words to seen set

    return filtered_keywords


def extract_keywords(client: DataScienceClient, text: str, num_keywords: int = 50):
    yake_kw_extractor = yake.KeywordExtractor(
        lan="en",
        top=num_keywords,
        dedupLim=1,
        stopwords=client.ignore_list,
    )
    keywords = yake_kw_extractor.extract_keywords(text.lower())

    keywords = [
        (pair[0], pair[1]) if type(pair[0]) != str else (pair[1], pair[0])
        for pair in keywords
    ]  # this pair comes on in a different order depending on your operating system

    keywords = _remove_substring_entries(keywords)
    return keywords


def get_emoji_match_scores(client: DataScienceClient, keywords: list[str]):
    emoji_match_scores = []

    for keyword in keywords:
        _keyword = client.nlp(keyword[1])  # Process keyword text
        keyword_scores = []

        for emoji_index in range(len(client.emojis)):

            # Check if emoji is in keyword or vice versa
            if any(
                word == client.emojis[emoji_index]["description"].lower()
                for word in keyword[1].lower().split()
            ) or any(
                word == keyword[1].lower()
                for word in client.emojis[emoji_index]["description"].lower().split()
            ):
                emoji_match_score = 1.0  # Set max similarity score
            else:
                emoji_match_score = _keyword.similarity(
                    client.emoji_nlp[emoji_index]
                )  # Otherwise, use semantic similarity

            keyword_scores.append(
                [
                    _keyword,
                    emoji_match_score,
                    client.emojis[emoji_index]["emoji"],
                ]
            )

        # Sort emoji matches by highest similarity
        # and append best match to emoji_match_scores
        keyword_scores.sort(key=lambda x: -x[1])
        emoji_match_scores.append(keyword_scores[0])

    # Sort overall results by highest similarity, and clip them
    emoji_match_scores.sort(key=lambda x: -x[1])
    emoji_match_scores = emoji_match_scores[:10]
    return emoji_match_scores


def join_description_and_emoji_score(text_lines: list[str], emoji_match_scores: list):
    emoji_descriptions = []
    for emoji_score in emoji_match_scores:
        keyword: spacy_doc.Doc = emoji_score[0]
        emoji = emoji_score[2]
        for quote in text_lines:
            if str(keyword) in quote:
                emoji_descriptions.append(
                    [
                        emoji,
                        keyword,
                        quote,
                    ]
                )
                break
    return emoji_descriptions
