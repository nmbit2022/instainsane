"""
Coordinador del equipo de agentes.

Corre cada agente de estrategia por separado, los combina en un "ensemble"
(decisión por consenso) y hace el backtest de todos aplicando el mismo gestor
de riesgo. Devuelve los resultados para compararlos.
"""
from __future__ import annotations

import pandas as pd

from engine.backtester import BacktestResult, buy_and_hold, run_backtest
from .base import BaseAgent
from .breakout import Breakout
from .mean_reversion import MeanReversion
from .risk_manager import RiskManager
from .trend_follower import TrendFollower


class Coordinator:
    def __init__(self, agents: list[BaseAgent] | None = None,
                 risk: RiskManager | None = None):
        self.agents = agents or [TrendFollower(), MeanReversion(), Breakout()]
        self.risk = risk or RiskManager()

    def ensemble_signal(self, df: pd.DataFrame) -> pd.Series:
        """Consenso: promedio de las señales de todos los agentes (conviction)."""
        signals = [a.generate_signals(df) for a in self.agents]
        combined = pd.concat(signals, axis=1).mean(axis=1)
        return combined.fillna(0.0)

    def run(self, df: pd.DataFrame) -> list[BacktestResult]:
        """Backtestea cada agente, el ensemble y la referencia buy & hold."""
        results: list[BacktestResult] = []

        for agent in self.agents:
            sig = agent.generate_signals(df)
            results.append(run_backtest(df, sig, agent.name, self.risk))

        ensemble = self.ensemble_signal(df)
        results.append(run_backtest(df, ensemble, "EQUIPO (consenso)", self.risk))

        results.append(buy_and_hold(df))
        return results
