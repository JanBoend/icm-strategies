"""Smoke tests for strategy classes: interface, indicator building, backtest execution."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd
import pytest

from strategies.amd import AMDStrategy
from strategies.fvg import FVGStrategy
from strategies.ifvg import iFVGStrategy
from strategies.orb import ORBStrategy

STRATEGIES = [AMDStrategy, FVGStrategy, iFVGStrategy, ORBStrategy]


def _make_ohlc(periods=2000, freq="15min", seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2023-01-02", periods=periods, freq=freq)
    close = 100 + np.cumsum(rng.normal(0, 0.3, periods))
    high = close + rng.uniform(0.05, 0.3, periods)
    low = close - rng.uniform(0.05, 0.3, periods)
    open_ = close + rng.normal(0, 0.1, periods)
    return pd.DataFrame({"Open": open_, "High": high, "Low": low, "Close": close}, index=idx)


LTF = _make_ohlc()
HTF = LTF["Close"].resample("4h").last().to_frame("Close").dropna()


@pytest.mark.parametrize("cls", STRATEGIES)
def test_default_params_returns_dict(cls):
    strat = cls()
    assert isinstance(strat.params, dict)
    assert strat.params["initial_capital"] == 10_000


@pytest.mark.parametrize("cls", STRATEGIES)
def test_params_override(cls):
    strat = cls({"risk_pct": 0.01})
    assert strat.params["risk_pct"] == 0.01


@pytest.mark.parametrize("cls", STRATEGIES)
def test_build_indicators_and_backtest_run(cls):
    strat = cls()
    indicators = strat.build_indicators(LTF, HTF) if cls is FVGStrategy else strat.build_indicators(LTF)

    assert isinstance(indicators, pd.DataFrame)
    assert len(indicators) > 0

    equity, trades = strat.run_backtest(indicators)
    assert isinstance(equity, pd.Series)
    assert isinstance(trades, pd.DataFrame)
    assert len(equity) == len(indicators)
