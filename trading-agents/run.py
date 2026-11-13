"""
Punto de entrada: corre el equipo de agentes sobre datos de oro y compara.

Uso:
    python run.py                         # usa data/gold_sample.csv (sintético)
    python run.py --data data/gold.csv    # usa tus datos reales
    python run.py --plot                  # guarda un gráfico de las curvas
    python run.py --no-short              # solo posiciones largas
"""
from __future__ import annotations

import argparse
import os

from agents import Breakout, Coordinator, MeanReversion, RiskManager, TrendFollower
from engine.data_loader import load_csv
from engine.metrics import format_metrics


def main() -> None:
    ap = argparse.ArgumentParser(description="Equipo de agentes de trading (backtest de oro).")
    ap.add_argument("--data", default="data/gold_sample.csv", help="CSV OHLCV.")
    ap.add_argument("--target-vol", type=float, default=0.15, help="Volatilidad objetivo anual.")
    ap.add_argument("--max-drawdown", type=float, default=0.20, help="Kill-switch de drawdown.")
    ap.add_argument("--cost", type=float, default=0.0005, help="Costo por cambio de posición.")
    ap.add_argument("--no-short", action="store_true", help="Solo largos (sin ponerse corto).")
    ap.add_argument("--plot", action="store_true", help="Guardar gráfico en reports/.")
    args = ap.parse_args()

    if not os.path.exists(args.data):
        raise SystemExit(
            f"No existe {args.data}.\n"
            "Genera datos de prueba con:  python generate_data.py\n"
            "o descarga reales con:       python fetch_data.py"
        )

    df = load_csv(args.data)
    print(f"Datos: {args.data}  |  {len(df)} días  |  "
          f"{df.index[0].date()} -> {df.index[-1].date()}\n")

    allow_short = not args.no_short
    agents = [
        TrendFollower(allow_short=allow_short),
        MeanReversion(allow_short=allow_short),
        Breakout(allow_short=allow_short),
    ]
    risk = RiskManager(target_vol=args.target_vol, max_drawdown=args.max_drawdown)
    coordinator = Coordinator(agents=agents, risk=risk)
    results = coordinator.run(df)

    print("=" * 100)
    print("RESULTADOS DEL BACKTEST (oro)")
    print("=" * 100)
    for r in results:
        print(f"{r.name:>20} | {format_metrics(r.metrics)}")
    print("=" * 100)
    print("Guía rápida: Sharpe alto = buen retorno por riesgo. MaxDD = peor caída.")
    print("'EQUIPO (consenso)' combina a los tres agentes; 'comprar y mantener' es la referencia.")

    if args.plot:
        make_plot(results)


def make_plot(results) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(matplotlib no instalado; omito el gráfico. pip install matplotlib)")
        return

    os.makedirs("reports", exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6))
    for r in results:
        style = "--" if r.name == "comprar y mantener" else "-"
        lw = 2.5 if r.name.startswith("EQUIPO") else 1.5
        ax.plot(r.equity.index, r.equity.values, style, linewidth=lw, label=r.name)
    ax.set_title("Curvas de capital — equipo de agentes sobre oro")
    ax.set_ylabel("Capital (inicio = 1.0)")
    ax.set_yscale("log")
    ax.legend()
    ax.grid(True, alpha=0.3)
    out = "reports/equity_curves.png"
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    print(f"\nGráfico guardado en {out}")


if __name__ == "__main__":
    main()
