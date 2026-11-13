"""
Análisis walk-forward (optimización rodante).

En vez de una sola división pasado/futuro, rueda una ventana por toda la
historia: en cada paso ELIGE la mejor configuración usando solo el pasado
(ventana de entrenamiento) y la PRUEBA en el tramo siguiente que no vio
(ventana de prueba). Luego pega todos los tramos de prueba en una sola curva.

Eso estima de forma honesta lo que habrías ganado operando de verdad y
reajustando cada cierto tiempo. Es el estándar de la industria.

Uso:
    python walkforward.py --data data/gold.csv --no-short --plot
    python walkforward.py --data data/gold.csv --train-years 4 --test-years 1
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

from agents import Breakout, MeanReversion, RiskManager, TrendFollower
from engine.backtester import run_backtest
from engine.data_loader import load_csv
from engine.metrics import TRADING_DAYS, compute_metrics, format_metrics

WARMUP = 200  # días de calentamiento para los indicadores lentos (EMA 200, etc.)


def build_candidates(allow_short: bool):
    """Catálogo de configuraciones candidatas a elegir en cada ventana."""
    cands = []
    for fast, slow in [(10, 50), (20, 100), (50, 200), (20, 50)]:
        cands.append((f"tend{fast}/{slow}", TrendFollower(fast, slow, allow_short)))
    for w, lo, hi in [(14, 30, 70), (14, 25, 75), (7, 20, 80)]:
        cands.append((f"rev{w}/{lo}-{hi}", MeanReversion(w, lo, hi, allow_short=allow_short)))
    for w in [10, 20, 55]:
        cands.append((f"brk{w}", Breakout(w, allow_short)))
    return cands


def _sharpe(returns: pd.Series) -> float:
    std = returns.std()
    return float(returns.mean() / std * np.sqrt(TRADING_DAYS)) if std > 0 else 0.0


def walk_forward(df: pd.DataFrame, train_days: int, test_days: int,
                 allow_short: bool, risk: RiskManager):
    """Rueda la ventana y devuelve la serie de retornos fuera de muestra."""
    candidates = build_candidates(allow_short)
    n = len(df)
    oos_returns = []      # retornos diarios fuera de muestra, pegados
    segments = []         # info de cada tramo de prueba

    cursor = 0
    while cursor + train_days + test_days <= n:
        tr0, tr1 = cursor, cursor + train_days
        te0, te1 = tr1, min(tr1 + test_days, n)
        train = df.iloc[tr0:tr1]

        # 1) Elegir la mejor config SOLO con el entrenamiento (por Sharpe).
        best_name, best_agent, best_sharpe = None, None, -np.inf
        for name, agent in candidates:
            res = run_backtest(train, agent.generate_signals(train), name, risk)
            s = res.metrics.get("sharpe", 0.0)
            if s > best_sharpe:
                best_name, best_agent, best_sharpe = name, agent, s

        # 2) Probar esa config en el tramo siguiente (con calentamiento previo).
        look0 = max(0, te0 - WARMUP)
        test_slice = df.iloc[look0:te1]
        res = run_backtest(test_slice, best_agent.generate_signals(test_slice),
                           best_name, risk)
        test_ret = res.returns.iloc[-(te1 - te0):]  # solo el tramo de prueba
        oos_returns.append(test_ret)

        segments.append({
            "desde": df.index[te0].date(),
            "hasta": df.index[te1 - 1].date(),
            "elegido": best_name,
            "sharpe_train": best_sharpe,
            "sharpe_test": _sharpe(test_ret),
            "retorno_test": float((1 + test_ret).prod() - 1),
        })
        cursor += test_days

    if not oos_returns:
        raise SystemExit("No hay suficientes datos para el walk-forward. "
                         "Baja --train-years o --test-years.")

    wf_ret = pd.concat(oos_returns)
    wf_equity = (1 + wf_ret).cumprod()
    return wf_ret, wf_equity, segments


def main() -> None:
    ap = argparse.ArgumentParser(description="Análisis walk-forward del equipo.")
    ap.add_argument("--data", default="data/gold.csv")
    ap.add_argument("--train-years", type=float, default=4.0)
    ap.add_argument("--test-years", type=float, default=1.0)
    ap.add_argument("--no-short", action="store_true")
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.data):
        raise SystemExit(f"No existe {args.data}. Descarga datos con fetch_data.py.")

    df = load_csv(args.data)
    train_days = int(args.train_years * TRADING_DAYS)
    test_days = int(args.test_years * TRADING_DAYS)
    allow_short = not args.no_short
    risk = RiskManager()

    print(f"Datos: {args.data}  |  {len(df)} días  |  "
          f"{df.index[0].date()} -> {df.index[-1].date()}")
    print(f"Entrena {args.train_years} años, prueba {args.test_years} año(s), "
          f"rodando hacia adelante.\n")

    wf_ret, wf_equity, segments = walk_forward(df, train_days, test_days,
                                               allow_short, risk)

    print("=" * 92)
    print("TRAMOS FUERA DE MUESTRA (cada uno con la config elegida solo con el pasado)")
    print("=" * 92)
    print(f"{'Prueba':>23} | {'Config elegida':>14} | {'Sharpe train':>12} | "
          f"{'Sharpe test':>11} | {'Retorno':>8}")
    print("-" * 92)
    for s in segments:
        print(f"{str(s['desde'])+' -> '+str(s['hasta']):>23} | {s['elegido']:>14} | "
              f"{s['sharpe_train']:>12.2f} | {s['sharpe_test']:>11.2f} | "
              f"{s['retorno_test']*100:>7.1f}%")
    print("=" * 92)

    # Métricas globales del walk-forward (la curva fuera de muestra pegada).
    wf_pos = (wf_ret != 0).astype(float)  # aprox. de exposición para métricas
    wf_metrics = compute_metrics(wf_equity, wf_ret, wf_pos)

    # Comparar con comprar y mantener en el MISMO periodo fuera de muestra.
    bh_close = df["Close"].loc[wf_equity.index]
    bh_equity = bh_close / bh_close.iloc[0]
    bh_ret = bh_equity.pct_change().fillna(0.0)
    bh_metrics = compute_metrics(bh_equity, bh_ret, pd.Series(1.0, index=bh_equity.index))

    print("\nRESULTADO GLOBAL (todos los tramos de prueba pegados):")
    print(f"{'WALK-FORWARD (equipo)':>22} | {format_metrics(wf_metrics)}")
    print(f"{'comprar y mantener':>22} | {format_metrics(bh_metrics)}")
    print("\nLa fila WALK-FORWARD es lo más cercano a lo que habrías ganado operando")
    print("de verdad, reajustando la config cada año con solo el pasado disponible.")

    if args.plot:
        _plot(wf_equity, bh_equity)


def _plot(wf_equity: pd.Series, bh_equity: pd.Series) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("\n(matplotlib no instalado; omito el gráfico.)")
        return
    os.makedirs("reports", exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(wf_equity.index, wf_equity.values, "-", linewidth=2.5,
            label="Walk-forward (equipo)")
    ax.plot(bh_equity.index, bh_equity.values, "--", linewidth=1.5,
            label="comprar y mantener")
    ax.set_title("Walk-forward fuera de muestra vs comprar y mantener (oro)")
    ax.set_ylabel("Capital (inicio = 1.0)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    out = "reports/walkforward.png"
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    print(f"\nGráfico guardado en {out}")


if __name__ == "__main__":
    main()
