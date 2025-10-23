"""Deterministic backtest utilities for equal-weight portfolios."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Iterable, List

import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend for tests and headless envs
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

plt.style.use("seaborn-v0_8")

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


def rolling_sharpe_series(daily_returns: Iterable[float], window: int = 21) -> List[float]:
    """Compute rolling Sharpe ratios with the supplied window."""
    returns_list = list(daily_returns)
    if not returns_list:
        return []

    ratios: List[float] = []
    for idx in range(len(returns_list)):
        if idx + 1 < window:
            ratios.append(0.0)
            continue
        window_slice = returns_list[idx + 1 - window : idx + 1]
        mean_return = sum(window_slice) / window
        variance = sum((r - mean_return) ** 2 for r in window_slice) / window
        std_dev = math.sqrt(variance)
        if std_dev == 0.0:
            ratios.append(0.0)
        else:
            ratios.append((mean_return / std_dev) * math.sqrt(252))
    return ratios


def drawdown_series(curve: Iterable[float]) -> List[float]:
    """Return drawdown values (negative when below prior peak)."""
    drawdowns: List[float] = []
    peak = 0.0
    for value in curve:
        peak = max(peak, value)
        drawdowns.append(value - peak)
    return drawdowns


def _plot_series(x, y, title: str, ylabel: str, filepath: Path) -> None:
    """Helper to plot a single series to disk."""
    plt.figure(figsize=(8, 4))
    plt.plot(x, y, color="#38bdf8", linewidth=2)
    plt.fill_between(x, y, alpha=0.15, color="#38bdf8")
    plt.title(title)
    plt.xlabel("Days")
    plt.ylabel(ylabel)
    plt.grid(alpha=0.2)
    plt.tight_layout()
    filepath.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(filepath)
    plt.close()


def _plot_drawdown(x, drawdowns: List[float], filepath: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.fill_between(x, drawdowns, 0, color="#f97316", alpha=0.3, step="pre")
    ax.plot(x, drawdowns, color="#f97316", linewidth=1.5)
    ax.set_title("Drawdown (vs. running peak)")
    ax.set_xlabel("Days")
    ax.set_ylabel("Drawdown")
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.grid(alpha=0.2)
    ax.set_ylim(min(drawdowns + [0]) * 1.1, 0.01)
    plt.tight_layout()
    filepath.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(filepath)
    plt.close()


def save_backtest_plots(
    cumulative_curve: Iterable[float],
    rolling_sharpe: Iterable[float],
    drawdowns: Iterable[float],
    plot_dir: Path,
) -> Dict[str, str]:
    """Persist backtest plots to the static plots directory."""
    plot_dir.mkdir(parents=True, exist_ok=True)
    curve_list = list(cumulative_curve)
    rolling_list = list(rolling_sharpe)
    drawdown_list = list(drawdowns)
    x_axis = list(range(1, len(curve_list) + 1))

    cumulative_path = plot_dir / "cumulative_return.png"
    rolling_path = plot_dir / "rolling_sharpe.png"
    drawdown_path = plot_dir / "drawdown.png"

    _plot_series(x_axis, curve_list, "Cumulative Return", "Return", cumulative_path)
    _plot_series(x_axis, rolling_list, "Rolling Sharpe (21d)", "Sharpe", rolling_path)
    _plot_drawdown(x_axis, drawdown_list, drawdown_path)

    return {
        "cumulative": str(cumulative_path),
        "rolling_sharpe": str(rolling_path),
        "drawdown": str(drawdown_path),
    }


def run_backtest(
    weights: Dict[str, float],
    returns: Dict[str, Iterable[float]],
    storage_dir: Path = Path("storage"),
    plot_dir: Path = Path("app/static/plots"),
) -> Dict[str, float]:
    """Run a simple equal-weight backtest and persist weight CSV."""
    storage_dir.mkdir(parents=True, exist_ok=True)
    weights_path = storage_dir / "portfolio_weights.csv"
    serialize_weights(weights, str(weights_path))

    daily_returns = compute_portfolio_returns(weights, returns)
    curve = cumulative_returns(daily_returns)

    sharpe = annualized_sharpe(daily_returns)
    drawdown = max_drawdown(curve)
    rolling_series = rolling_sharpe_series(daily_returns)
    drawdowns = drawdown_series(curve)
    plots = save_backtest_plots(curve, rolling_series, drawdowns, plot_dir)

    return {
        "sharpe": sharpe,
        "max_drawdown": drawdown,
        "final_return": round(curve[-1], 4) if curve else 0.0,
        "days": len(daily_returns),
        "plots": plots,
    }
