"""Simple equal-weight selector based on agent consensus decisions."""

from __future__ import annotations

from typing import Dict


def equal_weight_selection(decisions: Dict[str, str]) -> Dict[str, float]:
    """Allocate equal weights to tickers with BUY decisions."""
    buy_tickers = [ticker.upper() for ticker, decision in decisions.items() if decision.upper() == "BUY"]
    if not buy_tickers:
        return {}
    weight = 1.0 / len(buy_tickers)
    return {ticker: weight for ticker in buy_tickers}


def serialize_weights(weights: Dict[str, float], filepath: str) -> None:
    """Persist portfolio weights to disk as CSV."""
    lines = ["ticker,weight"]
    for ticker, weight in weights.items():
        lines.append(f"{ticker},{weight:.6f}")
    with open(filepath, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
