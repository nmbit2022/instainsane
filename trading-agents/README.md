# Equipo de agentes de trading — Backtesting de XAUUSD 🪙

Un **grupo de agentes** donde cada uno es una estrategia con un rol distinto, más
un **gestor de riesgo** y un **coordinador** que los corre a todos, los combina por
consenso y compara resultados sobre datos históricos de **oro (XAUUSD)**.

> ⚠️ **Esto NO es asesoría financiera ni un sistema que opera solo con tu dinero.**
> Es una herramienta de **backtesting**: prueba ideas sobre el pasado para
> entenderlas antes de arriesgar nada. Que algo funcione en el pasado **no**
> garantiza que funcione en el futuro. El trading tiene riesgo real de pérdida.

## El equipo

| Agente | Rol | Cómo decide |
|---|---|---|
| 🏇 **Tendencia** (`trend_follower.py`) | Montarse en tendencias largas | Cruce de medias EMA (rápida vs lenta) |
| ↩️ **Reversión** (`mean_reversion.py`) | Comprar barato / vender caro en rangos | RSI (sobreventa/sobrecompra) |
| 🚀 **Ruptura** (`breakout.py`) | Entrar cuando rompe niveles clave | Canal de Donchian (máx/mín de N días) |
| 🛡️ **Riesgo** (`risk_manager.py`) | Que nadie te arruine | Tamaño por volatilidad + stop-loss ATR + kill-switch de drawdown |
| 🎯 **Coordinador** (`coordinator.py`) | Dirige al equipo | Corre a todos y los combina por consenso |

La idea: cada estrategia funciona bien en un tipo de mercado y mal en otro.
Combinarlas con buena gestión de riesgo suele dar resultados **más estables**
que cualquiera por separado.

## Instalación

```bash
cd trading-agents
pip install -r requirements.txt
```

Mínimo necesitas `pandas` y `numpy`. `yfinance` y `matplotlib` son opcionales
(para datos reales y gráficos).

## Uso rápido (con datos de prueba)

```bash
python generate_data.py      # crea data/gold_sample.csv (oro sintético)
python run.py                # corre el equipo y muestra la tabla comparativa
python run.py --plot         # además guarda un gráfico en reports/
```

Salida de ejemplo:

```
           tendencia | Retorno   -8.0% | Sharpe -0.14 | MaxDD -20.1% | Trades 238
           reversion | Retorno  -17.5% | Sharpe -0.50 | MaxDD -20.2% | Trades 126
             ruptura | Retorno  -14.6% | Sharpe -0.26 | MaxDD -20.2% | Trades 252
   EQUIPO (consenso) | Retorno   29.2% | Sharpe  0.40 | MaxDD -13.5% | Trades 1502
  comprar y mantener | Retorno   38.5% | Sharpe  0.28 | MaxDD -45.5% | Trades 1
```

*(Números con datos sintéticos, solo para demostrar el motor.)*

## Usar datos REALES de XAUUSD

Mercado objetivo: **XAUUSD** (oro spot contra el dólar). En tu máquina (sin el
bloqueo de red del entorno de la nube):

```bash
python fetch_data.py                    # auto: prueba varias fuentes hasta que una funcione
# si quieres forzar una fuente:
python fetch_data.py --source stooq     # XAUUSD spot vía Stooq
python fetch_data.py --source yfinance --symbol GC=F   # futuro de oro (COMEX)

python run.py --data data/gold.csv --plot
```

> Si falla la descarga, el script te muestra qué fuente falló y por qué, más
> sugerencias. Suele ser el antivirus/VPN o una fuente temporalmente caída.

## Opciones útiles

```bash
python run.py --no-short            # solo posiciones largas (sin ponerse corto)
python run.py --target-vol 0.10    # apuntar a menos volatilidad (más conservador)
python run.py --max-drawdown 0.15  # kill-switch más estricto
python run.py --cost 0.001         # costos de transacción más altos
```

## Cómo leer las métricas

- **Sharpe**: retorno por unidad de riesgo. Más alto = mejor. >1 es bueno, >2 muy bueno.
- **MaxDD (max drawdown)**: la peor caída desde un pico. Más chico (menos negativo) = mejor.
- **CAGR**: rendimiento anual compuesto.
- **WinRate**: % de días ganadores.
- **Trades**: número de operaciones (más operaciones = más costos).

## Estructura

```
trading-agents/
├── run.py              # punto de entrada: corre el equipo y compara
├── generate_data.py    # datos de oro sintéticos (offline)
├── fetch_data.py       # datos de oro reales (yfinance / stooq)
├── agents/
│   ├── base.py             # clase base de agente
│   ├── trend_follower.py   # 🏇 tendencia
│   ├── mean_reversion.py   # ↩️ reversión
│   ├── breakout.py         # 🚀 ruptura
│   ├── risk_manager.py     # 🛡️ gestión de riesgo
│   └── coordinator.py      # 🎯 coordinador del equipo
├── engine/
│   ├── indicators.py   # EMA, RSI, ATR, Donchian, volatilidad
│   ├── backtester.py   # motor de simulación (costos, stops, kill-switch)
│   ├── metrics.py      # Sharpe, drawdown, etc.
│   └── data_loader.py  # carga CSV
└── tests/
    └── test_backtester.py
```

## Cómo agregar tu propia estrategia

1. Crea `agents/mi_estrategia.py` heredando de `BaseAgent`.
2. Implementa `generate_signals(df)` devolviendo una serie de `{-1, 0, 1}`.
3. Añádela a la lista de agentes en `run.py`.

```python
from agents.base import BaseAgent
import pandas as pd

class MiEstrategia(BaseAgent):
    name = "mi_estrategia"
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        pos = pd.Series(0.0, index=df.index)
        # tu lógica aquí...
        return pos
```

## Próximos pasos posibles

- Optimización de parámetros (walk-forward) para no sobreajustar.
- Simulación en tiempo real (*paper trading*) con datos en vivo.
- Más agentes: momentum cruzado, estacionalidad del oro, correlación con el dólar (DXY).
- Un agente "analista" basado en LLM que resuma noticias y contexto macro.

---
*Herramienta educativa de backtesting. No es asesoría de inversión.*
