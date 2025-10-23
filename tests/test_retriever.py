"""Tests for the mock retriever implementation."""

from __future__ import annotations

from data.indices.retriever import MockRetriever


def test_retriever_returns_structured_snippets() -> None:
    retriever = MockRetriever()
    results = retriever.search("AAPL guidance", ticker="AAPL", k=5)
    assert results, "Expected at least one snippet"
    top = results[0]
    assert top["ticker"] == "AAPL"
    assert top["source"] in {"filing", "news", "price"}
    assert "content" in top and top["content"]
    assert "title" in top
    assert "id" in top
