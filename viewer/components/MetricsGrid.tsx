import type { Metrics } from "@/lib/types";
import { Stat } from "./ui/Stat";
import { fmtNum, fmtPct, fmtUsd, fmtX } from "@/lib/format";

export function MetricsGrid({ metrics }: { metrics: Metrics }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
      <Stat label="CAGR" value={fmtPct(metrics.cagr)} tone={metrics.cagr >= 0 ? "pos" : "neg"} />
      <Stat label="Sharpe" value={fmtNum(metrics.sharpe)} />
      <Stat label="Sortino" value={fmtNum(metrics.sortino)} />
      <Stat label="Calmar" value={fmtNum(metrics.calmar)} />
      <Stat label="Max Drawdown" value={fmtPct(metrics.max_drawdown)} tone="neg" />
      <Stat
        label="DD Duration"
        value={`${metrics.max_drawdown_duration.bars} bars`}
        sub={metrics.max_drawdown_duration.censored ? "ongoing" : undefined}
      />
      <Stat label="Hit Rate" value={fmtPct(metrics.hit_rate)} />
      <Stat label="Avg Win" value={fmtUsd(metrics.avg_win)} tone="pos" />
      <Stat label="Avg Loss" value={fmtUsd(metrics.avg_loss)} tone="neg" />
      <Stat label="Exposure" value={fmtPct(metrics.exposure)} />
      <Stat label="Turnover" value={fmtX(metrics.turnover)} />
      <Stat label="Deflated Sharpe" value={fmtNum(metrics.deflated_sharpe.dsr)} sub={`n=${metrics.deflated_sharpe.n_trials}`} />
    </div>
  );
}
