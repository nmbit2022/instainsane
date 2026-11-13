"""Clase base para todos los agentes de estrategia."""
from __future__ import annotations

import pandas as pd


class BaseAgent:
    """
    Un agente es una estrategia con un rol.

    Cada agente mira el histórico de precios y decide una posición objetivo
    por cada día:
        +1  -> comprado (largo, apuesta a que sube)
         0  -> fuera del mercado (plano)
        -1  -> vendido (corto, apuesta a que baja)

    El backtester luego simula qué habría pasado siguiendo esas decisiones.
    """

    name: str = "base"
    description: str = "Agente base (sin lógica)."

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """Devuelve una serie de posiciones objetivo {-1, 0, 1} indexada como df."""
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Agent {self.name}>"
