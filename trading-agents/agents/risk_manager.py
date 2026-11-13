"""Agente gestor de riesgo."""
from __future__ import annotations

import pandas as pd

from engine.indicators import realized_vol


class RiskManager:
    """
    Rol: que ninguna estrategia te arruine.

    No decide dirección (eso lo hacen los otros agentes); decide CUÁNTO
    arriesgar y cuándo cortar pérdidas. Hace tres cosas:

    1. Volatility targeting: ajusta el tamaño de la posición para apuntar a
       una volatilidad anual objetivo. Si el oro se vuelve muy volátil,
       reduce el tamaño; si está tranquilo, lo sube (con un tope).
    2. Stop-loss por ATR: el backtester cierra la posición si el precio se
       mueve en contra más de `stop_atr` veces el ATR desde la entrada.
    3. Kill-switch por drawdown: si la cuenta cae más de `max_drawdown`,
       el backtester se pone plano un tiempo (enfriamiento).

    Los parámetros 2 y 3 los lee el backtester desde este objeto.
    """

    name = "riesgo"
    description = "Gestión de riesgo: tamaño por volatilidad + stops + kill-switch."

    def __init__(self, target_vol: float = 0.15, max_leverage: float = 1.5,
                 vol_window: int = 20, stop_atr: float = 3.0,
                 max_drawdown: float = 0.20, cooldown: int = 10,
                 stop_cooldown: int = 5):
        self.target_vol = target_vol
        self.max_leverage = max_leverage
        self.vol_window = vol_window
        self.stop_atr = stop_atr
        self.max_drawdown = max_drawdown
        self.cooldown = cooldown
        # Días de enfriamiento tras un stop antes de poder reentrar. Evita
        # quedar bloqueado fuera de una tendencia larga por un solo stop.
        self.stop_cooldown = stop_cooldown

    def size(self, df: pd.DataFrame) -> pd.Series:
        """Multiplicador de tamaño (>=0) por volatilidad objetivo."""
        rv = realized_vol(df["Close"], self.vol_window)
        scale = (self.target_vol / rv).clip(upper=self.max_leverage)
        return scale.fillna(0.0)
