"""
Motor de backtesting.

Simula, día a día, qué habría pasado si hubieras seguido las decisiones de un
agente. Aplica costos de transacción, stop-loss por ATR y un kill-switch por
drawdown (del gestor de riesgo). Evita el "lookahead": la posición decidida con
los datos del día t solo gana/pierde con el movimiento del día t+1.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from agents.risk_manager import RiskManager
from .indicators import atr
from .metrics import compute_metrics


@dataclass
class BacktestResult:
    name: str
    equity: pd.Series        # curva de capital (empieza en 1.0)
    returns: pd.Series       # retorno diario de la estrategia
    position: pd.Series      # exposición efectiva por día
    metrics: dict


def run_backtest(
    df: pd.DataFrame,
    signal: pd.Series,
    name: str,
    risk: RiskManager | None = None,
    cost_per_turn: float = 0.0005,   # 5 pips/bps por cambio de posición
) -> BacktestResult:
    """Corre un backtest sobre `df` siguiendo `signal` (posiciones objetivo)."""
    risk = risk or RiskManager()
    close = df["Close"].to_numpy(dtype=float)
    ret = np.zeros(len(df))
    ret[1:] = close[1:] / close[:-1] - 1.0

    atr_series = atr(df, risk.vol_window).to_numpy()
    raw = signal.reindex(df.index).fillna(0.0).to_numpy()
    size = risk.size(df).to_numpy()

    n = len(df)
    pos = np.zeros(n)          # exposición efectiva mantenida en cada día
    equity = np.ones(n)

    held = 0.0                 # posición actual
    entry_price = np.nan       # precio de entrada de la posición actual
    stop_cd = 0                # días de enfriamiento restantes tras un stop
    cooldown_left = 0          # días restantes de enfriamiento por kill-switch
    peak = 1.0

    for t in range(n):
        # 1) Ganancia/pérdida del día con la posición que traíamos de ayer.
        pnl = held * ret[t]
        eq = equity[t - 1] if t > 0 else 1.0
        eq_after = eq * (1 + pnl)

        # 2) Kill-switch por drawdown.
        peak = max(peak, eq_after)
        if cooldown_left == 0 and eq_after / peak - 1 < -risk.max_drawdown:
            cooldown_left = risk.cooldown

        # 3) Decidir la posición objetivo para mañana.
        target = raw[t] * size[t]

        if cooldown_left > 0:
            target = 0.0
            cooldown_left -= 1

        # 4) Enfriamiento tras un stop: unos pocos días plano, luego se puede
        #    reentrar si la señal sigue vigente (no se bloquea toda la tendencia).
        if stop_cd > 0:
            target = 0.0
            stop_cd -= 1
        # 5) Stop-loss por ATR sobre la posición abierta.
        elif held != 0 and not np.isnan(entry_price) and not np.isnan(atr_series[t]):
            adverse = (entry_price - close[t]) if held > 0 else (close[t] - entry_price)
            if adverse > risk.stop_atr * atr_series[t]:
                target = 0.0
                stop_cd = risk.stop_cooldown

        # 6) Costo por cambiar de posición.
        turn = abs(target - held)
        eq_after *= (1 - turn * cost_per_turn)

        # 7) Registrar entrada nueva.
        if np.sign(target) != np.sign(held) and target != 0:
            entry_price = close[t]
        elif target == 0:
            entry_price = np.nan

        held = target
        pos[t] = held
        equity[t] = eq_after

    equity_s = pd.Series(equity, index=df.index)
    strat_ret = equity_s.pct_change().fillna(0.0)
    pos_s = pd.Series(pos, index=df.index)
    metrics = compute_metrics(equity_s, strat_ret, pos_s)
    return BacktestResult(name, equity_s, strat_ret, pos_s, metrics)


def buy_and_hold(df: pd.DataFrame) -> BacktestResult:
    """Referencia: comprar y mantener el oro todo el periodo."""
    close = df["Close"]
    equity = close / close.iloc[0]
    ret = equity.pct_change().fillna(0.0)
    pos = pd.Series(1.0, index=df.index)
    return BacktestResult("comprar y mantener", equity, ret, pos,
                          compute_metrics(equity, ret, pos))
