"""Simple mock retriever returning context snippets for prompts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class MockRetriever:
    """Keyword-based retriever over a small mock corpus."""

    corpus_paths: Dict[str, Path] = field(
        default_factory=lambda: {
            "filing": Path("data/mock/filings.txt"),
            "news": Path("data/mock/news.txt"),
            "price": Path("data/mock/prices.txt"),
        }
    )

    def search(self, query: str, k: int = 3) -> List[Dict[str, str]]:
        query_lower = query.lower()
        candidates: List[Dict[str, str]] = []
        for source, path in self.corpus_paths.items():
            if not path.exists():
                continue
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    text = line.strip()
                    if not text:
                        continue
                    score = self._score(query_lower, text)
                    candidates.append({
                        "source": source,
                        "content": text,
                        "score": score,
                    })

        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates[:k]

    def _score(self, query: str, text: str) -> float:
        words = re.findall(r"[a-z0-9]+", query)
        if not words:
            return 0.0
        hits = sum(word in text.lower() for word in words)
        return hits / len(words)


default_retriever = MockRetriever()
