"""
Probar estrategias de gráfico (análisis técnico clásico) sobre el oro.

Backtestea cuatro señales famosas de los libros de trading y las compara con
'comprar y mantener'. Con --split hace prueba fuera de muestra para ver si lo
que funciona en el pasado se sostiene en el futuro.

Uso:
    python chart_test.py --data data/gold.csv --no-short
    python chart_test.py --data data/gold.csv --no-short --split 0.6
    python chart_test.py --data data/gold.csv --no-short --start 2013-07-01 --end 2019-05-31
"""
from __future__ import annotations

import argparse
import os

import pandas as pd

from agents import RiskManager
from agents.chart_patterns import BollingerBounce, Engulfing, GoldenCross, MACDCross
from engine.backtester import buy_and_hold, run_backtest
from engine.data_loader import load_csv
from engine.metrics import format_metrics


def _agents(allow_short: bool):
    return [
        GoldenCross(allow_short=allow_short),
        MACDCross(allow_short=allow_short),
        BollingerBounce(allow_short=allow_short),
        Engulfing(allow_short=allow_short),
    ]


def _run_and_print(df, agents, risk, titulo):
    print("=" * 100)
    print(titulo)
    print("=" * 100)
    for a in agents:
        res = run_backtest(df, a.generate_signals(df), a.name, risk)
        print(f"{a.name:>14} | {format_metrics(res.metrics)}")
    bh = buy_and_hold(df)
    print(f"{bh.name:>14} | {format_metrics(bh.metrics)}")
    print("=" * 100)


def main() -> None:
    ap = argparse.ArgumentParser(description="Probar estrategias de gráfico.")
    ap.add_argument("--data", default="data/gold.csv")
    ap.add_argument("--no-short", action="store_true")
    ap.add_argument("--split", type=float, default=None, metavar="FRAC")
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    args = ap.parse_args()

    if not os.path.exists(args.data):
        raise SystemExit(f"No existe {args.data}. Descarga datos con fetch_data.py.")

    df = load_csv(args.data)
    if args.start:
        df = df.loc[df.index >= pd.Timestamp(args.start)]
    if args.end:
        df = df.loc[df.index <= pd.Timestamp(args.end)]
    if len(df) < 250:
        raise SystemExit("Muy pocos datos (se necesitan ~250 días).")

    allow_short = not args.no_short
    agents = _agents(allow_short)
    risk = RiskManager()

    print(f"Datos: {args.data}  |  {len(df)} días  |  "
          f"{df.index[0].date()} -> {df.index[-1].date()}\n")

    if args.split is not None:
        if not 0.2 <= args.split <= 0.8:
            raise SystemExit("--split debe estar entre 0.2 y 0.8.")
        cut = int(len(df) * args.split)
        df_in, df_out = df.iloc[:cut], df.iloc[cut:]
        _run_and_print(df_in, agents, risk,
                       f"PARTE 1 — DENTRO DE MUESTRA ({df_in.index[0].date()} -> {df_in.index[-1].date()})")
        print()
        _run_and_print(df_out, _agents(allow_short), risk,
                       f"PARTE 2 — FUERA DE MUESTRA  ({df_out.index[0].date()} -> {df_out.index[-1].date()})")
        print("\nSi una estrategia brilla en la Parte 1 pero falla en la Parte 2,")
        print("ese buen resultado era espejismo (sobreajuste).")
        return

    _run_and_print(df, agents, risk, "ESTRATEGIAS DE GRÁFICO (oro)")
    print("Guía: Sharpe alto = buen retorno por riesgo. MaxDD = peor caída.")
    print("¿Alguna le gana a 'comprar y mantener' de forma consistente?")


if __name__ == "__main__":
    main()
