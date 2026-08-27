<p align="center">
  <img src="assets/banner.svg" alt="Event-Driven Backtesting Engine — data flows through as_of(t), walk-forward, bias audit, an immutable bundle, then a static viewer" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/DuckDB-point--in--time%20store-fff000?logo=duckdb&logoColor=black" alt="DuckDB">
  <img src="https://img.shields.io/badge/next.js-14-000000?logo=next.js&logoColor=white" alt="Next.js 14">
  <img src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white" alt="TypeScript">
  <img src="https://img.shields.io/badge/backend-none%20at%20runtime-2dd4bf" alt="No runtime backend">
  <img src="https://img.shields.io/badge/pytest-0A9EDC?logo=pytest&logoColor=white" alt="pytest">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-a78bfa" alt="MIT License"></a>
</p>

<p align="center"><b>A backtesting engine whose defining feature is that look-ahead bias is structurally impossible to introduce — not avoided by convention, but blocked by the data-access interface itself. Every result ships with a bias &amp; cost audit, not just a Sharpe ratio.</b></p>

---

Most backtesting bugs aren't in the strategy logic — they're in the plumbing: a signal that
accidentally sees tomorrow's close, a fill priced at the same bar that generated the order, a
Sharpe ratio quietly inflated by trying 200 parameter combinations and reporting the best one. This
engine makes an entire class of those bugs impossible to write, rather than possible-but-discouraged:

- **Strategies can't see the future — the interface won't let them.** The only way a strategy
  reads market data is `DataHandler.as_of(t)`, which is bound to a replay clock that only the event
  loop advances. Asking for `t` beyond that clock doesn't return stale or empty data — it raises.
- **Fills can't happen on the bar that generated them — the same way.** An order decided at the
  close of bar *t* can only fill on a strictly later bar's open; the execution handler raises if
  that invariant is ever violated, rather than relying on call-order discipline elsewhere in the
  codebase.
- **Every reported Sharpe is accompanied by the audit that would catch it lying.** Deflated Sharpe
  Ratio and Probability of Backtest Overfitting (via CSCV) correct for how many parameter
  combinations were actually tried — a strategy that looks good only because it was one of 45
  trials gets flagged, not celebrated.

Two decoupled halves, joined only by an immutable, versioned bundle on disk: a Python compute
engine (event-driven simulation, walk-forward optimization, the bias auditor) and a Next.js static
viewer that renders that bundle and imports zero Python.

## Contents

- [Why this exists](#why-this-exists)
- [Screenshots](#screenshots)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [The no-look-ahead invariant](#the-no-look-ahead-invariant)
- [Walk-forward: purge + embargo](#walk-forward-purge--embargo)
- [The bias audit](#the-bias-audit)
- [Cost model](#cost-model)
- [Design principles](#design-principles)
- [Tech stack](#tech-stack)
- [Development](#development)
- [Deploy](#deploy)
- [Disclaimer](#disclaimer)
- [License](#license)

## Why this exists

Backtests are notoriously easy to make look good and hard to make honest. The usual failure modes
— look-ahead leakage, same-bar fills, ignoring transaction costs, and reporting the best of many
parameter searches as if it were a single held-out result — all quietly inflate performance in the
same direction, and none of them show up by eyeballing an equity curve. This project treats "can
this backtest lie to me" as the central engineering problem, not an afterthought: the invariants
that prevent leakage are enforced by the type of interface a strategy is handed, not by a linter or
a code-review checklist, and the report format makes the audit as prominent as the returns.

## Screenshots

**Overview — Strengths/Caveats box driven by the bias audit, and the metrics grid**

![Dashboard overview: header, strengths/caveats box, and metrics grid](assets/screenshots/dashboard-overview.png)

**Equity & Drawdown — gross vs. net vs. buy-and-hold benchmark**

![Equity chart with gross, net, and benchmark lines](assets/screenshots/equity-drawdown.png)

## Architecture

```mermaid
flowchart LR
    subgraph Engine [engine/ -- Python, local only]
        DATA[data/\nDuckDB: raw prices +\nadjustment factors, separate tables]
        EVENTS[events/\nMarketEvent to SignalEvent\nto OrderEvent to FillEvent]
        STRAT[strategy/\nas_of(t)-only access]
        PORT[portfolio/ + execution/\nnext-bar fills only]
        COSTS[costs/\ncommission + spread + impact]
        WF[walkforward/\nrolling/anchored, purge + embargo]
        AUDIT[audit/\nDeflated Sharpe, PBO via CSCV]
        METRICS[metrics/\nCAGR, Sharpe, Sortino, Calmar...]
        BUNDLE[bundle/\nwriter: manifest + hashes]
    end

    subgraph Viewer [viewer/ -- Next.js, static export]
        JSON[/public/data/current/*.json/]
        DASH[Dashboard: Recharts,\nzero Python imports]
    end

    DATA --> STRAT --> EVENTS --> PORT
    PORT --> COSTS --> WF --> AUDIT
    WF --> METRICS
    AUDIT --> BUNDLE
    METRICS --> BUNDLE
    BUNDLE -->|immutable, versioned| JSON
    JSON --> DASH
```

The two halves are joined **only** by that bundle directory — `bundles/run_<id>/manifest.json,
metrics.json, equity.parquet, trades.parquet, sensitivity.json, bias_audit.json`. The viewer never
imports Python; it fetches static JSON at runtime, which is why it deploys as a plain static site
with no backend.

## Installation

```bash
git clone https://github.com/divyaanshkumar24/event-driven-backtesting-engine.git
cd event-driven-backtesting-engine

# Compute engine
make venv          # creates .venv (python3.11) and installs with dev extras

# Viewer
cd viewer && npm install
```

## Quickstart

```bash
# 1. Run the reference strategy end-to-end on real data (fetches & caches SPY via yfinance,
#    walk-forward optimizes, audits, writes a bundle + viewer data)
.venv/bin/python scripts/run_reference_backtest.py

# 2. View the report
cd viewer && npm run dev
```

Open `http://localhost:3000`.

## The no-look-ahead invariant

`DataHandler.as_of(t, symbol)` is the *only* data-access path a strategy is ever given. It wraps a
DuckDB store where every row carries a `knowledge_ts` distinct from its bar timestamp `ts` (so a
later phase can model vendor reporting lag without a schema change), and it tracks a replay clock
that only the event loop advances as bars are dispatched in strict time order:

```python
def as_of(self, t, symbol):
    if self._current_time is None:
        raise LookaheadError("replay clock has not started")
    if t > self._current_time:
        raise LookaheadError(f"requested t={t} is beyond the current replay clock")
    return self._store.query_as_of(symbol, t)
```

This is proven two ways, not just asserted: a Hypothesis property test checks that
`query_as_of` never returns a row with `knowledge_ts` after `t`, for randomized data and random
`t`; and a "leak canary" test has a fake strategy try to peek past the replay clock and asserts it
raises. The same pattern extends to fills — `ExecutionHandler` raises `SameBarFillError` if an
order's timestamp isn't strictly before the bar it's matched against — and to the walk-forward
optimizer, where the in-sample run's event queue is *bounded* to end at the purge boundary, so
`as_of()` calls during that run cannot see embargo/test-period data through any path, structurally,
not by post-hoc filtering.

## Walk-forward: purge + embargo

Rolling or anchored train/test folds, with the test window always starting exactly `test_bars`
after the previous one ends — no independent step size, so out-of-sample segments are adjacent by
construction (no gap, no overlap) regardless of mode. Purging and embargo prevent the two subtler
leaks walk-forward analysis is prone to:

- **Purge** — the in-sample optimization run's event stream simply stops `purge_bars` before the
  nominal end of the training window, so no trade's realized P&L can be influenced by price action
  close to the train/test boundary.
- **Embargo** — a gap of `embargo_bars` separates the (purged) training window from the test
  window, so the out-of-sample evaluation doesn't start on data serially correlated with what was
  just used for selection.

Verified by running two datasets that are identical up through the purge boundary but diverge
sharply afterward, and asserting the in-sample parameter selection is byte-identical between them.

## The bias audit

`bias_audit.json` reports nine fields, each as `{status, value, explanation}` — not just numbers,
but why they matter:

| Field | What it catches |
|---|---|
| `look_ahead_violations` | Always 0 — a violation raises and aborts the run rather than appearing in output |
| `fill_timing_assumption` | The fixed next-bar-open convention, stated explicitly |
| `survivorship_posture` | Flags the free-data limitation honestly rather than faking a delisted-universe comparison |
| `cost_analysis` | Gross vs. net Sharpe, annualized cost drag, and the cost multiple at which the edge breaks even |
| `turnover` | Traded notional as a multiple of average equity |
| `overfitting_analysis` | **Deflated Sharpe Ratio** and **Probability of Backtest Overfitting** (via CSCV) — corrects for how many parameter combinations were actually tried |
| `is_oos_degradation` | In-sample vs. out-of-sample Sharpe — a large gap means the optimizer found noise |
| `regime_breakdown` | OOS Sharpe split by trailing-volatility tercile |
| `capacity` | The AUM at which the strategy's own market impact would erode its edge to zero |

The Deflated Sharpe Ratio and PBO implementations are tested against synthetic scenarios with known
ground truth — a "lucky winner" among 50 pure-noise trials is correctly *not* endorsed once
corrected for the 50 trials tried, and a panel of genuinely-noise strategies correctly produces a
high PBO (≈ chance), while one with a persistent real edge produces a low one.

## Cost model

Every fill records an itemized cost breakdown, not a single slipped price: commission
(per-share / per-trade / bps), half-spread (bps on notional), and square-root market impact
(`Y·σ·√(Q/ADV)`). Impact's `σ`/ADV are computed from data as of the *order's* decision time, not
the fill bar — so a trade's own volume can't leak into what it costs to place it.

## Design principles

Enforced as standing rules for the whole build, not just aspirational:

| Principle | What it meant in practice |
|---|---|
| **Structural over conventional** | Invariants (no look-ahead, no same-bar fills, no boundary leakage) are enforced by what the interface *can* return, not by a rule everyone has to remember to follow |
| **Test-first for timing** | Any code touching data timing or fills got its leak-canary/property test written before or alongside the implementation |
| **Ask before assuming** | Fill convention, adjustment handling, sizing, delisting, purge/embargo semantics — each was a genuine ambiguous finance decision, confirmed explicitly rather than silently defaulted |
| **Local-first** | No cloud services, no live trading, no order routing — data cached to local disk, no network calls inside the event loop |
| **The viewer never imports Python** | The compute engine and the report viewer are joined only by an immutable bundle on disk; the viewer is a static site with zero backend |

## Tech stack

`Python 3.11+` · `pandas` · `polars` · `numpy` · `scipy` · `DuckDB` · `pyarrow` · `pytest` +
`hypothesis` — `Next.js 14 (App Router)` · `TypeScript` · `Tailwind CSS` · `Recharts` ·
`Framer Motion`

## Development

```bash
make test    # pytest (94 tests: property tests, leak canaries, synthetic-overfit stats, ...)
make lint    # ruff check

cd viewer && npm run build   # type-check + static export
```

## Deploy

Only `viewer/` is ever deployed — `engine/`, `bundles/`, and `data_cache/` stay local, by design.
To deploy on Vercel:

1. Import this repo into Vercel and set **Root Directory** to `viewer`.
2. Leave the build command as `next build` (the default) and install command as `npm install`. No
   environment variables are required.
3. `viewer/public/data/current/` — the JSON snapshot from a real run — is committed so the deployed
   demo has something to show; it's derived output, not source, but shipped intentionally for the
   public demo (see `engine/bundle/viewer_export.py`). Regenerate it with
   `scripts/run_reference_backtest.py` and redeploy to update the demo.

## Disclaimer

This is a portfolio/engineering project, not investment software. The reference strategy (SMA
crossover) is deliberately trivial — it exists only to exercise the event loop — and its walk-forward
result is not a recommendation; the bundle's own bias audit flags it as not surviving correction for
the parameter search that produced it (`overfitting_analysis`, `deflated_sharpe`). Nothing here is
investment advice.

## License

MIT — see [LICENSE](LICENSE).
