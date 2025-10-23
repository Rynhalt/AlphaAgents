"""Mock retriever that loads structured snippets for filings, news, and prices."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class MockRetriever:
    """Keyword-based retrieval over ticker-specific JSON snippets."""

    root: Path = Path("data/mock")
    cache: Dict[str, List[Dict[str, str]]] = field(default_factory=dict)

    def _load_corpus(self, ticker: str) -> List[Dict[str, str]]:
        ticker = ticker.upper()
        if ticker in self.cache:
            return self.cache[ticker]

        snippets: List[Dict[str, str]] = []
        ticker_dir = self.root / ticker
        if not ticker_dir.exists():
            self.cache[ticker] = snippets
            return snippets

        for path in ticker_dir.glob("*.json"):
            source = path.stem  # filings / news / prices
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            for item in data:
                snippets.append(
                    {
                        "id": item.get("id", ""),
                        "title": item.get("title", ""),
                        "date": item.get("date", ""),
                        "source": item.get("source", source),
                        "content": item.get("content", ""),
                    }
                )

        self.cache[ticker] = snippets
        return snippets

    def search(self, query: str, ticker: Optional[str] = None, k: int = 3) -> List[Dict[str, str]]:
        """Return top-k snippets matching the query."""
        query_lower = query.lower()
        candidates: List[Dict[str, str]] = []

        tickers = [ticker.upper()] if ticker else [d.name for d in self.root.iterdir() if d.is_dir()]

        for tkr in tickers:
            for snippet in self._load_corpus(tkr):
                score = self._score(query_lower, snippet["content"])
                if score > 0:
                    candidate = dict(snippet)
                    candidate["ticker"] = tkr
                    candidate["score"] = score
                    candidates.append(candidate)

        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates[:k]

    def _score(self, query: str, text: str) -> float:
        words = re.findall(r"[a-z0-9]+", query)
        if not words:
            return 0.0
        lower = text.lower()
        hits = sum(word in lower for word in words)
        return hits / len(words)


default_retriever = MockRetriever()
