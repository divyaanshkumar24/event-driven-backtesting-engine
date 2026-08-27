import type { EquityPoint } from "./types";

export interface DrawdownPoint {
  timestamp: string;
  drawdown: number;
}

/** Peak-to-trough decline of the net equity series, as a fraction (mirrors engine/metrics/core.py's max_drawdown/query shape for display, not audit). */
export function computeDrawdownSeries(equity: EquityPoint[]): DrawdownPoint[] {
  let runningMax = -Infinity;
  return equity.map((p) => {
    runningMax = Math.max(runningMax, p.net);
    const drawdown = runningMax > 0 ? p.net / runningMax - 1 : 0;
    return { timestamp: p.timestamp, drawdown };
  });
}

export interface CostTotals {
  commission: number;
  half_spread: number;
  impact: number;
  total: number;
}

export function sumCosts(trades: { commission: number; half_spread: number; impact: number }[]): CostTotals {
  const totals = trades.reduce(
    (acc, t) => {
      acc.commission += t.commission;
      acc.half_spread += t.half_spread;
      acc.impact += t.impact;
      return acc;
    },
    { commission: 0, half_spread: 0, impact: 0 }
  );
  return { ...totals, total: totals.commission + totals.half_spread + totals.impact };
}
