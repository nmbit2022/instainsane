"""
Coordinador del equipo de agentes.

Corre cada agente de estrategia por separado, los combina en dos "ensembles"
(consenso simple y consenso ADAPTATIVO) y hace el backtest de todos aplicando el
mismo gestor de riesgo. Devuelve los resultados para compararlos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.backtester import BacktestResult, buy_and_hold, run_backtest
from .base import BaseAgent
from .breakout import Breakout
from .mean_reversion import MeanReversion
from .risk_manager import RiskManager
from .trend_follower import TrendFollower


class Coordinator:
    def __init__(self, agents: list[BaseAgent] | None = None,
                 risk: RiskManager | None = None, adapt_window: int = 60):
        self.agents = agents or [TrendFollower(), MeanReversion(), Breakout()]
        self.risk = risk or RiskManager()
        # Ventana (días) para medir el rendimiento reciente de cada agente.
        self.adapt_window = adapt_window

    def ensemble_signal(self, df: pd.DataFrame) -> pd.Series:
        """Consenso simple: promedio (peso igual) de todas las señales."""
        signals = [a.generate_signals(df) for a in self.agents]
        combined = pd.concat(signals, axis=1).mean(axis=1)
        return combined.fillna(0.0)

    def adaptive_signal(self, df: pd.DataFrame) -> pd.Series:
        """
        Consenso ADAPTATIVO: pondera a cada agente según su rendimiento reciente.

        Para cada día usa SOLO el pasado (sin lookahead): mira cómo le fue a cada
        agente en los últimos `adapt_window` días y le da más peso a quien ganó.
        Si todos van perdiendo últimamente, reparte por igual.
        """
        mkt_ret = df["Close"].pct_change().fillna(0.0)
        w = self.adapt_window

        sigs, scores = {}, {}
        for a in self.agents:
            s = a.generate_signals(df)
            sigs[a.name] = s
            # PnL causal del agente: posición de ayer * retorno de hoy.
            pnl = s.shift(1).fillna(0.0) * mkt_ret
            # Rendimiento reciente, desplazado 1 día para no mirar el futuro.
            scores[a.name] = pnl.rolling(w, min_periods=w // 2).mean().shift(1)

        score_df = pd.DataFrame(scores)
        pos = score_df.clip(lower=0.0)              # solo cuentan los que ganan
        total = pos.sum(axis=1)
        weights = pos.div(total.replace(0.0, np.nan), axis=0)
        # Si nadie gana (o aún no hay historia), peso igual.
        weights = weights.fillna(1.0 / len(self.agents))

        combined = pd.Series(0.0, index=df.index)
        for a in self.agents:
            combined += weights[a.name].fillna(0.0) * sigs[a.name]
        return combined.fillna(0.0)

    def run(self, df: pd.DataFrame) -> list[BacktestResult]:
        """Backtestea cada agente, los dos ensembles y la referencia buy & hold."""
        results: list[BacktestResult] = []

        for agent in self.agents:
            sig = agent.generate_signals(df)
            results.append(run_backtest(df, sig, agent.name, self.risk))

        results.append(run_backtest(
            df, self.ensemble_signal(df), "EQUIPO (simple)", self.risk))
        results.append(run_backtest(
            df, self.adaptive_signal(df), "EQUIPO (adaptativo)", self.risk))

        results.append(buy_and_hold(df))
        return results
