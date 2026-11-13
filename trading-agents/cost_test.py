"""
Test de sensibilidad a los costos.

Corre el backtest con distintos niveles de costo por operación y muestra cómo
se derrumba la rentabilidad. Es la lección #1 del day trading: como operas
MUCHÍSIMAS veces, el costo por operación (comisión + spread) suele decidir si
ganas o pierdes.

Uso:
    python cost_test.py --data data/gold.csv --no-short
    python cost_test.py --data data/gold.csv --no-short --plot
"""
from __future__ import annotations

import argparse
import os

import pandas as pd

from agents import Breakout, Coordinator, MeanReversion, RiskManager, TrendFollower
from engine.backtester import run_backtest
from engine.data_loader import load_csv

# Niveles de costo por operación (ida+vuelta), en puntos básicos (1 bp = 0.01%).
COST_LEVELS_BP = [0, 1, 2, 5, 10, 25, 50, 100]


def main() -> None:
    ap = argparse.ArgumentParser(description="Sensibilidad a costos (day trading).")
    ap.add_argument("--data", default="data/gold.csv")
    ap.add_argument("--no-short", action="store_true")
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.data):
        raise SystemExit(f"No existe {args.data}. Descarga datos con fetch_data.py.")

    df = load_csv(args.data)
    if args.start:
        df = df.loc[df.index >= pd.Timestamp(args.start)]
    if args.end:
        df = df.loc[df.index <= pd.Timestamp(args.end)]

    allow_short = not args.no_short
    agents = [
        TrendFollower(allow_short=allow_short),
        MeanReversion(allow_short=allow_short),
        Breakout(allow_short=allow_short),
    ]
    risk = RiskManager()
    coord = Coordinator(agents=agents, risk=risk)

    # Señales de cada estrategia + el equipo (no dependen del costo).
    strategies = {a.name: a.generate_signals(df) for a in agents}
    strategies["EQUIPO"] = coord.ensemble_signal(df)

    print(f"Datos: {args.data}  |  {len(df)} días  |  "
          f"{df.index[0].date()} -> {df.index[-1].date()}")
    print("Retorno total (%) según el costo por operación:\n")

    # Cabecera.
    header = f"{'Costo/op':>10} | " + " | ".join(f"{name:>10}" for name in strategies)
    print(header)
    print("-" * len(header))

    # Guardar nº de operaciones (con costo medio) para el análisis.
    trades = {}
    rows = {}
    for bp in COST_LEVELS_BP:
        cost = bp / 10000.0
        cells = []
        for name, sig in strategies.items():
            res = run_backtest(df, sig, name, risk, cost_per_turn=cost)
            ret = res.metrics.get("total_return", 0.0) * 100
            cells.append(f"{ret:>9.1f}%")
            if bp == 0:
                trades[name] = res.metrics.get("trades", 0)
        rows[bp] = cells
        label = f"{bp:>3} bp" + ("  (0%)" if bp == 0 else "")
        print(f"{label:>10} | " + " | ".join(cells))

    print("\n(1 bp = 0.01%. '0 bp' = mundo ideal sin costos.)")
    print("Nº de operaciones por estrategia (en todo el periodo):")
    for name, n in trades.items():
        print(f"  {name:>10}: {n} operaciones")

    print("\n== POR QUÉ ESTO IMPORTA EN DAY TRADING ==")
    print("Arriba operaste pocas veces en años. Un day trader hace esa misma")
    print("cantidad de operaciones en SEMANAS. Como el costo se paga en CADA")
    print("operación, al multiplicar la frecuencia multiplicas el costo total:")
    print("una estrategia rentable a 2 bp puede ser ruinosa si operas 50x más.")

    if args.plot:
        _plot(df, strategies, risk)


def _plot(df, strategies, risk) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(matplotlib no instalado; omito el gráfico.)")
        return
    os.makedirs("reports", exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 6))
    costs = [bp / 10000.0 for bp in COST_LEVELS_BP]
    for name, sig in strategies.items():
        rets = []
        for c in costs:
            res = run_backtest(df, sig, name, risk, cost_per_turn=c)
            rets.append(res.metrics.get("total_return", 0.0) * 100)
        ax.plot(COST_LEVELS_BP, rets, marker="o", label=name)
    ax.axhline(0, color="gray", linewidth=1, linestyle="--")
    ax.set_xlabel("Costo por operación (puntos básicos)")
    ax.set_ylabel("Retorno total (%)")
    ax.set_title("Cómo los costos destruyen la rentabilidad")
    ax.legend()
    ax.grid(True, alpha=0.3)
    out = "reports/cost_sensitivity.png"
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    print(f"\nGráfico guardado en {out}")


if __name__ == "__main__":
    main()
