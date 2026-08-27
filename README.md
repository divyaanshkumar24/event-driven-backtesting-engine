# Event-Driven Walk-Forward Backtesting Engine

A backtesting engine whose defining feature is that look-ahead bias is
structurally impossible, not merely avoided by convention. Every result
ships with a bias & cost audit.

## Architecture

Two decoupled halves joined only by an immutable, versioned report bundle
on disk:

- **Compute engine** (`engine/`, Python): a time-ordered priority queue of
  `MarketEvent -> SignalEvent -> OrderEvent -> FillEvent`, a point-in-time
  DuckDB data layer, a pluggable cost model, a walk-forward runner, and a
  bias auditor. Emits a bundle: `manifest.json`, `metrics.json`,
  `equity.parquet`, `trades.parquet`, `sensitivity.json`, `bias_audit.json`.
- **Viewer** (`viewer/`, Next.js, static export): reads a bundle and
  renders a report. Never imports Python. An optional local FastAPI
  server may support live re-runs but is never load-bearing.

## Invariants

- Strategies access market data only through an `as_of(t)` interface that
  cannot return a bar with timestamp `> t`. This is enforced in code and
  proven by tests, not a convention.
- Fill timing: decisions are made at the close of bar `t` using data `<= t`;
  orders execute at the open (or VWAP) of bar `t+1`. Same-bar close-to-close
  fills are forbidden.
- No network calls inside the event loop. All data is cached to local disk.
- No cloud services, no deployment, no live trading or order routing.

## Layout

```
engine/
  data/         point-in-time data layer (DuckDB-backed)
  events/       event types and the event queue
  strategy/     strategy interface, as_of(t) data access
  portfolio/    position/cash tracking
  execution/    order -> fill simulation
  costs/        pluggable cost/slippage models
  walkforward/  walk-forward split runner
  audit/        bias auditor
  metrics/      performance metrics
tests/
bundles/        generated report bundles (gitignored, dir tracked)
viewer/         Next.js static viewer (later phase)
```

## Development

```
make venv    # create .venv (python3.11) and install with dev extras
make test    # run pytest
make lint    # run ruff check
make format  # run ruff format
```

## Status

Phase 0: repo scaffold. No engine logic yet.
