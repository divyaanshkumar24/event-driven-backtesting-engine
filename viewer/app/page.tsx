"use client";

import { useBundleData } from "@/lib/useBundleData";
import { Header } from "@/components/Header";
import { StrengthsCaveats } from "@/components/StrengthsCaveats";
import { MetricsGrid } from "@/components/MetricsGrid";
import { Tabs } from "@/components/Tabs";
import { Overview } from "@/components/tabs/Overview";
import { EquityDrawdown } from "@/components/tabs/EquityDrawdown";
import { Costs } from "@/components/tabs/Costs";
import { Sensitivity } from "@/components/tabs/Sensitivity";
import { WalkForward } from "@/components/tabs/WalkForward";
import { Trades } from "@/components/tabs/Trades";
import { Benchmark } from "@/components/tabs/Benchmark";

export default function Page() {
  const { data, error, loading } = useBundleData();

  if (loading) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-10">
        <p className="num text-sm text-muted">loading bundle…</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="mx-auto max-w-6xl px-6 py-10">
        <div className="rounded border border-neg bg-neg-soft px-4 py-3 text-sm text-neg">
          Failed to load bundle data: {error ?? "unknown error"}. Expected JSON files under
          <code className="mx-1 rounded bg-white px-1 py-0.5">public/data/current/</code>
          — run <code className="rounded bg-white px-1 py-0.5">scripts/run_reference_backtest.py</code> to produce
          one.
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-8">
      <Header manifest={data.manifest} />

      <section>
        <h2 className="label-caps mb-2 text-xs font-semibold text-muted">Strengths &amp; Caveats</h2>
        <StrengthsCaveats audit={data.biasAudit} />
      </section>

      <section>
        <h2 className="label-caps mb-2 text-xs font-semibold text-muted">Key Ratios</h2>
        <MetricsGrid metrics={data.metrics} />
      </section>

      <section>
        <Tabs
          tabs={[
            { id: "overview", label: "Overview", content: <Overview data={data} /> },
            { id: "equity", label: "Equity & Drawdown", content: <EquityDrawdown data={data} /> },
            { id: "costs", label: "Costs", content: <Costs data={data} /> },
            { id: "sensitivity", label: "Sensitivity", content: <Sensitivity sensitivity={data.sensitivity} /> },
            { id: "walkforward", label: "Walk-Forward", content: <WalkForward audit={data.biasAudit} /> },
            { id: "trades", label: "Trades", content: <Trades trades={data.trades} /> },
            {
              id: "benchmark",
              label: "vs. Benchmark",
              content: <Benchmark equity={data.equity} symbol={data.manifest.inputs.symbol} />,
            },
          ]}
        />
      </section>
    </main>
  );
}
