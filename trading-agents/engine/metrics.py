"""Métricas de rendimiento de una estrategia."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def compute_metrics(equity: pd.Series, returns: pd.Series,
                    position: pd.Series) -> dict:
    """
    Calcula las métricas clave a partir de la curva de capital y los retornos.

    - total_return: ganancia total (%).
    - cagr: rendimiento anual compuesto (%).
    - sharpe: retorno ajustado por riesgo (cuanto más alto, mejor; >1 es bueno).
    - sortino: como Sharpe pero penalizando solo las caídas.
    - max_drawdown: peor caída desde un pico (%). Mientras más chico, mejor.
    - volatility: volatilidad anualizada (%).
    - win_rate: % de días ganadores entre los días con posición.
    - exposure: % del tiempo dentro del mercado.
    - trades: número de operaciones (cambios de posición).
    """
    n = len(returns)
    if n == 0 or equity.empty:
        return {}

    total_return = equity.iloc[-1] / equity.iloc[0] - 1
    years = n / TRADING_DAYS
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else 0.0

    mean, std = returns.mean(), returns.std()
    sharpe = (mean / std * np.sqrt(TRADING_DAYS)) if std > 0 else 0.0

    downside = returns[returns < 0].std()
    sortino = (mean / downside * np.sqrt(TRADING_DAYS)) if downside and downside > 0 else 0.0

    roll_max = equity.cummax()
    drawdown = equity / roll_max - 1
    max_dd = drawdown.min()

    volatility = std * np.sqrt(TRADING_DAYS)

    active = returns[position.shift(1).fillna(0) != 0]
    win_rate = (active > 0).mean() if len(active) else 0.0
    exposure = (position != 0).mean()
    trades = int((position.diff().fillna(position.iloc[0]) != 0).sum())

    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_dd,
        "volatility": volatility,
        "win_rate": win_rate,
        "exposure": exposure,
        "trades": trades,
    }


def format_metrics(m: dict) -> str:
    """Formatea las métricas para imprimir en tabla."""
    if not m:
        return "(sin datos)"
    return (
        f"Retorno {m['total_return']*100:7.1f}% | "
        f"CAGR {m['cagr']*100:6.1f}% | "
        f"Sharpe {m['sharpe']:5.2f} | "
        f"MaxDD {m['max_drawdown']*100:6.1f}% | "
        f"WinRate {m['win_rate']*100:4.1f}% | "
        f"Trades {m['trades']:4d}"
    )
