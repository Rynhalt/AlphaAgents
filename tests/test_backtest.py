"""Tests for portfolio selection and backtesting utilities."""

from __future__ import annotations

from pathlib import Path

from portfolio.backtest import run_backtest
from portfolio.selector import equal_weight_selection


def test_equal_weight_selection_filters_buy_decisions() -> None:
    decisions = {"AAPL": "BUY", "MSFT": "SELL", "TSLA": "BUY"}
    weights = equal_weight_selection(decisions)
    assert weights == {"AAPL": 0.5, "TSLA": 0.5}


def test_run_backtest_generates_metrics_and_weights(tmp_path: Path) -> None:
    weights = {"AAPL": 0.5, "TSLA": 0.5}
    returns = {
        "AAPL": [0.01, 0.015, -0.005, 0.012],
        "TSLA": [0.02, -0.01, 0.005, 0.018],
    }

    metrics = run_backtest(weights, returns, storage_dir=tmp_path)
    weights_file = tmp_path / "portfolio_weights.csv"

    assert weights_file.exists()
    contents = weights_file.read_text(encoding="utf-8")
    assert "AAPL" in contents and "TSLA" in contents

    assert metrics["days"] == 4
    assert metrics["final_return"] > 0
    assert metrics["sharpe"] >= 0

