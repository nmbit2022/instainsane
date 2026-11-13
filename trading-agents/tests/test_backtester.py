"""Pruebas básicas del motor y los agentes."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import Breakout, Coordinator, MeanReversion, RiskManager, TrendFollower
from engine.backtester import buy_and_hold, run_backtest


def _toy_df(n: int = 400, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 1500 * np.exp(np.cumsum(0.0003 + 0.01 * rng.standard_normal(n)))
    idx = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close * 1.005,
            "Low": close * 0.995,
            "Close": close,
            "Volume": 1000,
        },
        index=idx,
    )


def test_agents_produce_valid_signals():
    df = _toy_df()
    for agent in (TrendFollower(), MeanReversion(), Breakout()):
        sig = agent.generate_signals(df)
        assert len(sig) == len(df)
        assert set(np.unique(sig.dropna())) <= {-1.0, 0.0, 1.0}


def test_backtest_runs_and_is_finite():
    df = _toy_df()
    res = run_backtest(df, TrendFollower().generate_signals(df), "t", RiskManager())
    assert len(res.equity) == len(df)
    assert np.isfinite(res.equity.to_numpy()).all()
    assert res.equity.iloc[0] > 0
    for key in ("sharpe", "max_drawdown", "total_return", "trades"):
        assert key in res.metrics


def test_no_lookahead_flat_signal_stays_flat():
    # Señal siempre plana -> capital constante (salvo nada de costos).
    df = _toy_df()
    flat = pd.Series(0.0, index=df.index)
    res = run_backtest(df, flat, "flat", RiskManager())
    assert abs(res.equity.iloc[-1] - 1.0) < 1e-9


def test_buy_and_hold_matches_price():
    df = _toy_df()
    res = buy_and_hold(df)
    expected = df["Close"].iloc[-1] / df["Close"].iloc[0]
    assert abs(res.equity.iloc[-1] - expected) < 1e-9


def test_coordinator_returns_all_results():
    df = _toy_df()
    results = Coordinator().run(df)
    # 3 agentes + ensemble simple + ensemble adaptativo + buy&hold
    assert len(results) == 6
    names = {r.name for r in results}
    assert "EQUIPO (simple)" in names
    assert "EQUIPO (adaptativo)" in names
    assert "comprar y mantener" in names


def test_walkforward_runs():
    from walkforward import walk_forward
    from agents import RiskManager
    df = _toy_df(n=1600)
    wf_ret, wf_equity, segments = walk_forward(
        df, train_days=500, test_days=250, allow_short=False, risk=RiskManager()
    )
    assert len(segments) >= 1
    assert len(wf_equity) > 0
    assert np.isfinite(wf_equity.to_numpy()).all()


if __name__ == "__main__":
    test_agents_produce_valid_signals()
    test_backtest_runs_and_is_finite()
    test_no_lookahead_flat_signal_stays_flat()
    test_buy_and_hold_matches_price()
    test_coordinator_returns_all_results()
    test_walkforward_runs()
    print("Todos los tests pasaron.")
