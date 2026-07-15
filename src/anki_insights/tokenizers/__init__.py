from __future__ import annotations

import re
from typing import Protocol, Set

import jieba
import spacy
from spacy.language import Language
from spacy.tokens import Token

try:
    from opencc import OpenCC
except ImportError:  # pragma: no cover
    OpenCC = None


class Tokenizer(Protocol):
    def tokenize(self, text: str) -> Set[str]: ...


class SpacyTokenizer:
    def __init__(self, model_name: str) -> None:
        self._nlp: Language = spacy.load(model_name)

    def _normalize(self, token: Token) -> str:
        if token.is_space or token.is_punct or token.like_num:
            return ""

        lemma = token.lemma_.lower().strip()
        return re.sub(r"^[^\w]+|[^\w]+$", "", lemma)

    def tokenize(self, text: str) -> Set[str]:
        return {
            normalized
            for token in self._nlp(text or "")
            if (normalized := self._normalize(token))
        }


class IndonesianTokenizer:
    def __init__(self) -> None:
        self._nlp: Language = spacy.blank("id")

    def _normalize(self, token: Token) -> str:
        if token.is_space or token.is_punct or token.like_num:
            return ""

        normalized = token.text.lower().strip()
        return re.sub(r"^[^\w]+|[^\w]+$", "", normalized)

    def tokenize(self, text: str) -> Set[str]:
        return {
            normalized
            for token in self._nlp(text or "")
            if (normalized := self._normalize(token))
        }


class MandarinTokenizer:
    _chinese_re = re.compile(r"[\u4e00-\u9fff]")

    def __init__(
        self,
        use_opencc: bool = True,
        opencc_config: str = "t2s",
        char_fallback: bool = True,
    ) -> None:
        self._char_fallback = char_fallback
        self._converter = OpenCC(opencc_config) if use_opencc and OpenCC else None

    def _normalize_script(self, text: str) -> str:
        return self._converter.convert(text) if self._converter else text

    def _contains_chinese(self, text: str) -> bool:
        return bool(self._chinese_re.search(text))

    def tokenize(self, text: str) -> Set[str]:
        normalized = self._normalize_script(text or "")
        tokens: Set[str] = set()

        for word in jieba.lcut(normalized, cut_all=False):
            token = word.strip()
            if not token:
                continue

            if self._contains_chinese(token):
                tokens.add(token)
                continue

            if self._char_fallback:
                tokens.update(ch for ch in token if self._contains_chinese(ch))

        return tokens
