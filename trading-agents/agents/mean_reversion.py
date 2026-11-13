"""Agente de reversión a la media (RSI)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.indicators import rsi
from .base import BaseAgent


class MeanReversion(BaseAgent):
    """
    Rol: comprar barato, vender caro dentro de un rango.

    Usa el RSI: cuando el precio está "sobrevendido" (RSI bajo) compra
    esperando un rebote, y cuando está "sobrecomprado" (RSI alto) se pone
    corto. Cierra la posición al volver a la zona neutra. Funciona bien en
    mercados laterales y mal en tendencias fuertes (por eso existe el equipo).
    """

    name = "reversion"
    description = "Reversión a la media con RSI."

    def __init__(self, window: int = 14, low: float = 30, high: float = 70,
                 exit_level: float = 50, allow_short: bool = True):
        self.window = window
        self.low = low
        self.high = high
        self.exit_level = exit_level
        self.allow_short = allow_short

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        r = rsi(df["Close"], self.window)
        pos = pd.Series(np.nan, index=df.index, dtype=float)

        pos[r < self.low] = 1.0                      # sobrevendido -> largo
        if self.allow_short:
            pos[r > self.high] = -1.0                # sobrecomprado -> corto

        # Cerrar (plano) al cruzar la zona neutra.
        pos[(r >= self.exit_level) & (r.shift(1) < self.exit_level)] = 0.0
        pos[(r <= self.exit_level) & (r.shift(1) > self.exit_level)] = 0.0

        # Mantener la última decisión hasta que haya una nueva.
        return pos.ffill().fillna(0.0)
