"""
Patrones horarios: cierre de Londres y apertura de NY.

Busca, en tus velas de 1h, los patrones de la franja institucional:
  1) Qué horas (UTC) mueven más y tienen más volumen.
  2) A qué hora se forman el MÁXIMO y el MÍNIMO del día (dónde se "cazan"
     los extremos / liquidez).
  3) Reversión del cierre de Londres: cuántas veces la dirección del solape
     (13-16 UTC) se da vuelta después del cierre de Londres (16-21 UTC).

Referencia horaria (según tu gráfico):
  Apertura NY = 13:00 UTC (10:00 ART) · Cierre Londres = 16:00 UTC (13:00 ART)
  Solape Londres-NY = 13:00-16:00 UTC (10:00-13:00 ART)

Uso:
    python patrones.py --data data/gold_1h.csv
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(description="Patrones horarios (Londres/NY).")
    ap.add_argument("--data", default="data/gold_1h.csv")
    args = ap.parse_args()
    if not os.path.exists(args.data):
        raise SystemExit(f"No existe {args.data}. Bájalo con: python fetch_intraday.py")

    df = pd.read_csv(args.data)
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True, errors="coerce")
    df = df.dropna(subset=["Datetime", "Close"]).sort_values("Datetime")
    df["hora"] = df["Datetime"].dt.hour
    df["dia"] = df["Datetime"].dt.date
    df["rango"] = (df["High"] - df["Low"]) / df["Close"] * 100
    df["ret"] = df["Close"].pct_change().abs() * 100

    ndias = df["dia"].nunique()
    print(f"Datos: {args.data}  |  {len(df)} velas  |  {ndias} días")
    print("Hora en UTC.  Apertura NY=13 · Cierre Londres=16  (restá 3h para ART)\n")

    # 1) Actividad por hora.
    g = df.groupby("hora").agg(rango=("rango", "mean"),
                               vol=("Volume", "mean"),
                               mov=("ret", "mean"))
    print("== ACTIVIDAD POR HORA (UTC) ==")
    print(f"{'Hora':>5} | {'Rango %':>8} | {'Volumen':>10} | {'|Mov| %':>8} | barra")
    mx = g["vol"].max()
    for h, r in g.iterrows():
        marca = "  « solape L-NY" if 13 <= h < 16 else "  (cierre Londres)" if h == 16 else ""
        barra = "█" * int(r["vol"] / mx * 20) if mx > 0 else ""
        print(f"{h:>4}h | {r['rango']:>7.3f}% | {r['vol']:>10,.0f} | {r['mov']:>7.3f}% | {barra}{marca}")

    # 2) A qué hora se forman los extremos del día.
    altos = df.loc[df.groupby("dia")["High"].idxmax()]["hora"].value_counts().head(3)
    bajos = df.loc[df.groupby("dia")["Low"].idxmin()]["hora"].value_counts().head(3)
    print("\n== ¿A QUÉ HORA SE FORMA EL EXTREMO DEL DÍA? ==")
    print("  Máximos del día (top horas):")
    for h, n in altos.items():
        print(f"    {h:>2}h UTC ({(h-3)%24:>2}h ART) → {n} días ({n/ndias*100:.0f}%)")
    print("  Mínimos del día (top horas):")
    for h, n in bajos.items():
        print(f"    {h:>2}h UTC ({(h-3)%24:>2}h ART) → {n} días ({n/ndias*100:.0f}%)")

    # 3) Reversión del cierre de Londres.
    piv = df.pivot_table(index="dia", columns="hora", values="Close", aggfunc="last")
    revs = total = 0
    for _, row in piv.iterrows():
        try:
            c13, c16, c20 = row[13], row[16], row[20]
        except KeyError:
            continue
        if any(pd.isna(x) for x in (c13, c16, c20)):
            continue
        total += 1
        if np.sign(c16 - c13) != np.sign(c20 - c16) and (c16 - c13) != 0:
            revs += 1
    print("\n== REVERSIÓN DEL CIERRE DE LONDRES ==")
    if total:
        print(f"  En {revs}/{total} días ({revs/total*100:.0f}%), la dirección del solape")
        print(f"  (13→16 UTC) se DIO VUELTA después del cierre de Londres (16→20 UTC).")
    else:
        print("  (no hay suficientes horas completas para medirlo)")

    print("\nContexto estadístico, no una garantía. Si el extremo del día suele")
    print("formarse en el solape, ahí es donde los grandes marcan la jugada.")


if __name__ == "__main__":
    main()
