"""Deterministic backtest utilities for equal-weight portfolios."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Iterable, List

from portfolio.selector import serialize_weights


def compute_portfolio_returns(
    weights: Dict[str, float],
    returns: Dict[str, Iterable[float]],
) -> List[float]:
    """Combine individual asset returns into a portfolio series."""
    if not weights:
        return []

    tickers = list(weights.keys())
    normalized_returns: Dict[str, List[float]] = {
        ticker: list(returns.get(ticker, [])) for ticker in tickers
    }
    series_length = len(next(iter(normalized_returns.values()), []))
    portfolio_returns: List[float] = []

    for idx in range(series_length):
        daily_return = 0.0
        for ticker in tickers:
            asset_returns = normalized_returns[ticker]
            if idx >= len(asset_returns):
                continue
            daily_return += weights[ticker] * asset_returns[idx]
        portfolio_returns.append(daily_return)
    return portfolio_returns


def cumulative_returns(daily_returns: Iterable[float]) -> List[float]:
    """Convert daily returns into a cumulative return curve."""
    total = 1.0
    curve: List[float] = []
    for r in daily_returns:
        total *= 1.0 + r
        curve.append(total - 1.0)
    return curve


def annualized_sharpe(daily_returns: Iterable[float]) -> float:
    """Compute simple annualized Sharpe ratio from daily returns."""
    daily_returns = list(daily_returns)
    if not daily_returns:
        return 0.0
    mean_return = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean_return) ** 2 for r in daily_returns) / len(daily_returns)
    std_dev = math.sqrt(variance)
    if std_dev == 0.0:
        return 0.0
    return round((mean_return / std_dev) * math.sqrt(252), 4)


def max_drawdown(curve: Iterable[float]) -> float:
    """Return the maximum drawdown from a cumulative return curve."""
    peak = -math.inf
    max_dd = 0.0
    for value in curve:
        peak = max(peak, value)
        max_dd = min(max_dd, value - peak)
    return round(abs(max_dd), 4)


def run_backtest(
    weights: Dict[str, float],
    returns: Dict[str, Iterable[float]],
    storage_dir: Path = Path("storage"),
) -> Dict[str, float]:
    """Run a simple equal-weight backtest and persist weight CSV."""
    storage_dir.mkdir(parents=True, exist_ok=True)
    weights_path = storage_dir / "portfolio_weights.csv"
    serialize_weights(weights, str(weights_path))

    daily_returns = compute_portfolio_returns(weights, returns)
    curve = cumulative_returns(daily_returns)

    sharpe = annualized_sharpe(daily_returns)
    drawdown = max_drawdown(curve)

    return {
        "sharpe": sharpe,
        "max_drawdown": drawdown,
        "final_return": round(curve[-1], 4) if curve else 0.0,
        "days": len(daily_returns),
    }
