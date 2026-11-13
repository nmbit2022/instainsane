"""Agente seguidor de tendencia (cruce de medias móviles)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.indicators import ema
from .base import BaseAgent


class TrendFollower(BaseAgent):
    """
    Rol: montarse en las tendencias.

    Compra cuando la media rápida cruza por encima de la lenta (tendencia
    alcista) y se pone corto cuando cruza por debajo. El oro suele tener
    tendencias largas, así que este agente busca aprovecharlas.
    """

    name = "tendencia"
    description = "Seguidor de tendencia por cruce de EMAs."

    def __init__(self, fast: int = 20, slow: int = 100, allow_short: bool = True):
        self.fast = fast
        self.slow = slow
        self.allow_short = allow_short

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        fast = ema(df["Close"], self.fast)
        slow = ema(df["Close"], self.slow)
        pos = pd.Series(0, index=df.index, dtype=float)
        pos[fast > slow] = 1.0
        pos[fast < slow] = -1.0 if self.allow_short else 0.0
        return pos.fillna(0.0)
