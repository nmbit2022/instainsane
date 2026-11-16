"""
Niveles y volumen: soportes/resistencias, zonas de acumulación y volúmenes
anormales. Contexto para decidir en el día a día.

  - Soportes/Resistencias: máximos y mínimos relevantes (pivotes) donde el precio
    reaccionó antes; suelen volver a frenar al precio.
  - Perfil de volumen: a qué PRECIOS se negoció más volumen (ahí se "acumuló"
    posición; suele ser soporte/resistencia fuerte). El de mayor volumen es el
    POC (Point of Control).
  - Volúmenes anormales: días con volumen muy por encima de lo normal; suelen
    marcar entrada de grandes jugadores (arriba = compradores, abajo = vendedores).

Uso:
    python levels.py --data data/gold.csv
    python levels.py --data data/gold.csv --lookback 250
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from engine.data_loader import load_csv


def pivots(df: pd.DataFrame, w: int = 10):
    """Pivotes: máximos/mínimos locales más altos/bajos que w barras a cada lado."""
    highs, lows = [], []
    H, L = df["High"].to_numpy(), df["Low"].to_numpy()
    for i in range(w, len(df) - w):
        if H[i] == H[i - w:i + w + 1].max():
            highs.append((df.index[i], H[i]))
        if L[i] == L[i - w:i + w + 1].min():
            lows.append((df.index[i], L[i]))
    return highs, lows


def volume_profile(df: pd.DataFrame, bins: int = 30):
    """Reparte el volumen por niveles de precio. Devuelve (centros, volumen por bin)."""
    price = df["Close"].to_numpy()
    vol = df["Volume"].to_numpy()
    lo, hi = price.min(), price.max()
    edges = np.linspace(lo, hi, bins + 1)
    idx = np.clip(np.digitize(price, edges) - 1, 0, bins - 1)
    vp = np.zeros(bins)
    for i, v in zip(idx, vol):
        vp[i] += v
    centers = (edges[:-1] + edges[1:]) / 2
    return centers, vp


def main() -> None:
    ap = argparse.ArgumentParser(description="Niveles y volumen (contexto diario).")
    ap.add_argument("--data", default="data/gold.csv")
    ap.add_argument("--lookback", type=int, default=250, help="Días hacia atrás a analizar.")
    ap.add_argument("--pivot-width", type=int, default=10)
    args = ap.parse_args()

    if not os.path.exists(args.data):
        raise SystemExit(f"No existe {args.data}. Descarga datos con fetch_data.py.")

    df = load_csv(args.data).tail(args.lookback)
    price = df["Close"].iloc[-1]
    print(f"Datos: {args.data}  |  últimos {len(df)} días  |  "
          f"precio actual: {price:,.2f}\n")

    # Rango del periodo y dónde está el precio dentro de él.
    rango_lo, rango_hi = float(df["Low"].min()), float(df["High"].max())
    pos_pct = (price - rango_lo) / (rango_hi - rango_lo) * 100 if rango_hi > rango_lo else 50
    print(f"Rango de {len(df)} días: {rango_lo:,.2f} (piso) .. {rango_hi:,.2f} (techo)")
    print(f"El precio está en el {pos_pct:.0f}% del rango "
          f"({'cerca de máximos' if pos_pct > 70 else 'cerca de mínimos' if pos_pct < 30 else 'en el medio'}).\n")

    # 1) Soportes y resistencias con distancia en %.
    highs, lows = pivots(df, args.pivot_width)
    res = sorted({round(float(p), 2) for _, p in highs if p > price})[:3]
    sup = sorted({round(float(p), 2) for _, p in lows if p < price}, reverse=True)[:3]
    # Si no hay pivote por debajo, el piso del rango es el soporte clave.
    if not sup:
        sup = [round(rango_lo, 2)]

    def con_dist(x):
        d = (x - price) / price * 100
        return f"{x:,.2f} ({d:+.1f}%)"

    print("== SOPORTES Y RESISTENCIAS ==")
    print(f"  Resistencias arriba: {', '.join(con_dist(x) for x in res) if res else 'ninguna (en máximos)'}")
    print(f"  >> Precio actual:    {price:,.2f}")
    print(f"  Soportes abajo:      {', '.join(con_dist(x) for x in sup)}")

    # 2) Perfil de volumen: zonas de acumulación.
    centers, vp = volume_profile(df)
    order = np.argsort(vp)[::-1]
    dist = lambda x: (x - price) / price * 100
    poc = centers[order[0]]
    arriba_abajo = "arriba → resistencia" if poc > price else "abajo → soporte"
    print("\n== ZONAS DE ACUMULACIÓN (más volumen negociado) ==")
    print(f"  POC (zona #1): {poc:,.2f} ({dist(poc):+.1f}%)  — imán más fuerte, está {arriba_abajo}")
    for rank, k in enumerate(order[1:3], start=2):
        print(f"  Zona #{rank}:      {centers[k]:,.2f} ({dist(centers[k]):+.1f}%)")

    # 3) Volúmenes anormales recientes.
    vol = df["Volume"]
    thresh = vol.mean() + 2 * vol.std()
    spikes = df[df["Volume"] > thresh].tail(5)
    print("\n== DÍAS DE VOLUMEN ANORMAL (posibles grandes jugadores) ==")
    if spikes.empty:
        print("  (ninguno reciente por encima del umbral)")
    else:
        for dt, row in spikes.iterrows():
            signo = "COMPRADORES ▲" if row["Close"] >= row["Open"] else "VENDEDORES ▼"
            print(f"  {dt.date()} | vol {row['Volume']:>12,.0f} | {signo} "
                  f"| cierre {row['Close']:,.2f}")

    print("\nContexto, no señales: estos niveles suelen frenar o acelerar al precio,")
    print("pero no garantizan nada. Úsalos junto con tu plan y tu gestión de riesgo.")


if __name__ == "__main__":
    main()
