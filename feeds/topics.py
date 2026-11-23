"""Phân loại chủ đề bài đăng theo từ khoá (không phân biệt hoa thường, theo ranh giới từ)."""
from __future__ import annotations

import re
from collections.abc import Mapping


class TopicMatcher:
    def __init__(self, topics: Mapping[str, list[str]], exclude: list[str]) -> None:
        self._topics = {name: self._pattern(words) for name, words in topics.items()}
        self._exclude = self._pattern(exclude) if exclude else None

    @staticmethod
    def _pattern(words: list[str]) -> re.Pattern:
        alternatives = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
        return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)", re.IGNORECASE)

    def topics(self, text: str) -> list[str]:
        """Các chủ đề mà bài nhắc tới, sau khi bỏ các cụm dễ nhầm trong `exclude`."""
        cleaned = self._exclude.sub(" ", text) if self._exclude else text
        return [name for name, pattern in self._topics.items() if pattern.search(cleaned)]
