"""Agente de ruptura (breakout de canal de Donchian)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.indicators import donchian
from .base import BaseAgent


class Breakout(BaseAgent):
    """
    Rol: entrar cuando el precio rompe un nivel importante.

    Si el cierre supera el máximo de las últimas N barras, compra (puede ser
    el inicio de un movimiento grande). Si rompe el mínimo, se pone corto.
    Es la estrategia clásica de las "tortugas" (turtle traders).
    """

    name = "ruptura"
    description = "Ruptura de canal de Donchian."

    def __init__(self, window: int = 20, allow_short: bool = True):
        self.window = window
        self.allow_short = allow_short

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        upper, lower = donchian(df, self.window)
        pos = pd.Series(np.nan, index=df.index, dtype=float)

        pos[df["Close"] > upper] = 1.0
        if self.allow_short:
            pos[df["Close"] < lower] = -1.0

        return pos.ffill().fillna(0.0)
