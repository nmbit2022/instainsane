"""
Análisis de sesiones: ¿en qué sesión (Asia / Londres / Nueva York) se mueve más
y más "limpio" el oro?

Usa datos de 1 hora (baja con fetch_intraday.py). Para cada sesión mide:
  - Movimiento: rango medio por hora (cuánto se mueve).
  - Volumen medio (actividad; más volumen = más instituciones).
  - Limpieza: 'efficiency ratio' de Kaufman (0 a 1). Alto = se mueve en una
    dirección clara (tendencia limpia). Bajo = sube y baja sin sentido (ruido).

Sesiones (en horario UTC, aproximado):
    Asia       00:00 - 08:00
    Londres    08:00 - 13:00
    NuevaYork  13:00 - 21:00   (incluye el solape Londres-NY, el más activo)

Uso:
    python session_analysis.py --data data/gold_1h.csv
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

SESSIONS = {
    "Asia": range(0, 8),
    "Londres": range(8, 13),
    "NuevaYork": range(13, 21),
}


def efficiency_ratio(closes: np.ndarray) -> float:
    """|cambio neto| / suma de |cambios|. 1 = tendencia perfecta, ~0 = puro ruido."""
    if len(closes) < 2:
        return np.nan
    net = abs(closes[-1] - closes[0])
    path = np.abs(np.diff(closes)).sum()
    return net / path if path > 0 else np.nan


def main() -> None:
    ap = argparse.ArgumentParser(description="Análisis de sesiones (intradía).")
    ap.add_argument("--data", default="data/gold_1h.csv")
    args = ap.parse_args()

    if not os.path.exists(args.data):
        raise SystemExit(f"No existe {args.data}. Bájalo con: python fetch_intraday.py")

    df = pd.read_csv(args.data)
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True, errors="coerce")
    df = df.dropna(subset=["Datetime", "Close"]).sort_values("Datetime")
    df["hour"] = df["Datetime"].dt.hour
    df["day"] = df["Datetime"].dt.date

    # Asignar cada vela a una sesión.
    def which(h):
        for name, hrs in SESSIONS.items():
            if h in hrs:
                return name
        return None
    df["session"] = df["hour"].map(which)
    df = df.dropna(subset=["session"])

    print(f"Datos: {args.data}  |  {len(df)} velas  |  "
          f"{df['Datetime'].iloc[0].date()} -> {df['Datetime'].iloc[-1].date()}")
    print("Horario en UTC. (Argentina = UTC-3; p. ej. 13:00 UTC = 10:00 en Argentina)\n")

    rows = []
    for name in SESSIONS:
        s = df[df["session"] == name]
        if s.empty:
            continue
        # Movimiento: rango medio por hora, en % del precio.
        rng = ((s["High"] - s["Low"]) / s["Close"] * 100)
        move = rng.mean()
        vol = s["Volume"].mean()
        # Limpieza: efficiency ratio por día y sesión, promediado.
        ers = s.groupby("day")["Close"].apply(lambda c: efficiency_ratio(c.to_numpy()))
        clean = ers.mean()
        rows.append((name, move, vol, clean))

    print("=" * 74)
    print(f"{'Sesión':>12} | {'Movimiento/h':>13} | {'Volumen medio':>14} | {'Limpieza':>9}")
    print(f"{'':>12} | {'(rango %)':>13} | {'(por hora)':>14} | {'(0-1)':>9}")
    print("-" * 74)
    for name, move, vol, clean in rows:
        print(f"{name:>12} | {move:>12.3f}% | {vol:>14,.0f} | {clean:>9.3f}")
    print("=" * 74)

    # Rankings.
    if rows:
        most_move = max(rows, key=lambda r: r[1])[0]
        most_vol = max(rows, key=lambda r: (r[2] if not np.isnan(r[2]) else -1))[0]
        cleanest = max(rows, key=lambda r: (r[3] if not np.isnan(r[3]) else -1))[0]
        print(f"\n🔊 Más movimiento:   {most_move}")
        print(f"🏦 Más volumen:      {most_vol}  (más actividad institucional)")
        print(f"✨ Más limpio:       {cleanest}  (tendencias más claras, menos ruido)")
        print("\nIdea: operar donde hay volumen y limpieza suele ser mejor que donde")
        print("el precio se mueve poco o va arriba-abajo sin dirección.")


if __name__ == "__main__":
    main()
