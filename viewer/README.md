# Viewer

Next.js 14 (app router), static export, no backend. Reads a bundle
produced by `engine/` and renders a screener.in-style report: a
Strengths/Caveats box driven by `bias_audit.json`, a compact metrics
grid, and tabs for Overview / Equity & Drawdown / Costs / Sensitivity /
Walk-Forward / Trades / vs. Benchmark.

The viewer's own code never imports Python. It fetches plain static
JSON files from `public/data/current/` at runtime (client-side
`fetch`), which works identically served from Vercel static hosting, a
plain S3 bucket, or `next dev`.

## Where the data comes from

`public/data/current/*.json` is a **generated, viewer-side** copy of a
bundle, not the bundle itself — the immutable `bundles/run_<id>/`
contract from the compute engine only has six files (manifest,
metrics, equity.parquet, trades.parquet, sensitivity, bias_audit), and
that's untouched by any of this.

Two things the viewer needs that aren't in the bundle proper (a gross
equity *curve*, and a buy-and-hold benchmark curve — only their
summary stats live in the bundle's own JSON) are derived by
`engine/bundle/viewer_export.py` from the same in-memory run that
wrote the bundle, and the two parquet files are converted to JSON
there too, so the browser never needs a parquet reader.

To (re)generate real data to view:

```bash
.venv/bin/python scripts/run_reference_backtest.py
```

This fetches/caches SPY data, runs the walk-forward, writes a bundle
to `bundles/`, and writes `viewer/public/data/current/`.

## Development

```bash
npm install
npm run dev     # http://localhost:3000
npm run build   # static export to out/
```

`public/data/current/` is gitignored (derived, not source) — run the
script above before `npm run dev` if it's empty.
