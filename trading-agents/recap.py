"""
Recap del día o la semana anterior (intradía).

Analiza las últimas 24 h o 7 días de velas de 1 hora para detectar:
  - Rango (máximo/mínimo) del periodo = soportes/resistencias de corto plazo.
  - Horas de VOLUMEN anormal (posibles grandes jugadores) y su dirección.
  - Zonas de precio donde más se negoció (dónde se acumuló posición).
  - Los movimientos de 1 hora más grandes (dónde se movió de golpe).

Necesita datos intradía: bájalos con  python fetch_intraday.py

Uso:
    python recap.py --period day      # el último día
    python recap.py --period week     # la última semana
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser(description="Recap del día/semana anterior (intradía).")
    ap.add_argument("--data", default="data/gold_1h.csv")
    ap.add_argument("--period", choices=["day", "week"], default="day")
    args = ap.parse_args()

    if not os.path.exists(args.data):
        raise SystemExit(f"No existe {args.data}. Bájalo con: python fetch_intraday.py")

    df = pd.read_csv(args.data)
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True, errors="coerce")
    df = df.dropna(subset=["Datetime", "Close"]).sort_values("Datetime")

    end = df["Datetime"].iloc[-1]
    # Usar las últimas velas DISPONIBLES (robusto ante fines de semana/feriados):
    # ~24h de mercado para 'day', ~1 semana de trading para 'week'.
    bars = 24 if args.period == "day" else 120
    win = df.tail(bars).copy()
    if len(win) < 3:
        raise SystemExit("Muy pocas velas. Baja datos intradía con: python fetch_intraday.py")

    hi, lo = win["High"].max(), win["Low"].min()
    first, last = win["Close"].iloc[0], win["Close"].iloc[-1]
    neta = (last / first - 1) * 100
    etiqueta = "ÚLTIMO DÍA" if args.period == "day" else "ÚLTIMA SEMANA"

    print(f"RECAP — {etiqueta}  ({win['Datetime'].iloc[0]:%d/%m %H:%M} → "
          f"{end:%d/%m %H:%M} UTC)  |  {len(win)} velas de 1h\n")

    # 1) Rango = soportes/resistencias de corto plazo.
    print("== RANGO DEL PERIODO (soporte/resistencia de corto plazo) ==")
    print(f"  Techo (resistencia): {hi:,.2f}")
    print(f"  Piso  (soporte):     {lo:,.2f}")
    print(f"  Cierre actual:       {last:,.2f}  |  movimiento neto: {neta:+.2f}%")

    # 2) Horas de volumen anormal (grandes jugadores).
    v = win["Volume"]
    thr = v.mean() + 2 * v.std()
    spikes = win[win["Volume"] > thr]
    print("\n== HORAS DE VOLUMEN ANORMAL (posibles grandes jugadores) ==")
    if spikes.empty:
        print("  (ninguna hora destacó mucho sobre el promedio)")
    else:
        for _, r in spikes.iterrows():
            signo = "COMPRADORES ▲" if r["Close"] >= r["Open"] else "VENDEDORES ▼"
            print(f"  {r['Datetime']:%d/%m %H:%M} UTC | vol {r['Volume']:>10,.0f} "
                  f"| {signo} | {r['Close']:,.2f}")

    # 3) Zonas de acumulación (mini perfil de volumen).
    price = win["Close"].to_numpy()
    vol = win["Volume"].to_numpy()
    bins = 12
    edges = np.linspace(lo, hi, bins + 1)
    idx = np.clip(np.digitize(price, edges) - 1, 0, bins - 1)
    vp = np.zeros(bins)
    for i, vv in zip(idx, vol):
        vp[i] += vv
    centers = (edges[:-1] + edges[1:]) / 2
    order = np.argsort(vp)[::-1]
    print("\n== ZONAS DONDE MÁS SE NEGOCIÓ (acumulación) ==")
    for rank, k in enumerate(order[:3], start=1):
        marca = "  ← POC (imán)" if rank == 1 else ""
        print(f"  Zona #{rank}: {centers[k]:,.2f}{marca}")

    # 4) Movimientos de 1 hora más grandes.
    win["chg"] = win["Close"].pct_change() * 100
    big = win.reindex(win["chg"].abs().sort_values(ascending=False).index).head(3)
    print("\n== MOVIMIENTOS DE 1 HORA MÁS BRUSCOS ==")
    for _, r in big.iterrows():
        d = "▲" if r["chg"] >= 0 else "▼"
        print(f"  {r['Datetime']:%d/%m %H:%M} UTC | {r['chg']:+.2f}% {d} | cierre {r['Close']:,.2f}")

    print("\nContexto, no señales. Úsalo para ubicar dónde reaccionó el precio y")
    print("dónde hubo volumen fuerte (posible huella de grandes jugadores).")


if __name__ == "__main__":
    main()
