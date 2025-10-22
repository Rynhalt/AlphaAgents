"""Tests for the mock retriever implementation."""

from __future__ import annotations

from data.indices.retriever import MockRetriever


def test_retriever_returns_top_chunks() -> None:
    retriever = MockRetriever()
    results = retriever.search("AAPL guidance", k=3)
    assert len(results) == 3
    top = results[0]
    assert "AAPL" in top["content"]
    assert top["source"] in {"filing", "news", "price"}
