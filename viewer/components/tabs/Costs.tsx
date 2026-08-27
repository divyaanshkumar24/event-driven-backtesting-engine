"use client";

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { BundleData } from "@/lib/types";
import { Card } from "../ui/Card";
import { Stat } from "../ui/Stat";
import { sumCosts } from "@/lib/derive";
import { fmtNum, fmtPct, fmtUsd, fmtX } from "@/lib/format";

const COLORS = ["#4664e0", "#94A3B8", "#DC2626"];

export function Costs({ data }: { data: BundleData }) {
  const totals = sumCosts(data.trades);
  const costAnalysis = data.biasAudit.cost_analysis.value;
  const chartData = [
    { name: "Commission", amount: totals.commission },
    { name: "Half-spread", amount: totals.half_spread },
    { name: "Impact", amount: totals.impact },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Gross Sharpe" value={fmtNum(costAnalysis.gross_sharpe)} />
        <Stat label="Net Sharpe" value={fmtNum(costAnalysis.net_sharpe)} tone="neg" />
        <Stat label="Annualized Cost Drag" value={fmtPct(costAnalysis.annualized_cost_drag)} tone="neg" />
        <Stat
          label="Breakeven Cost Multiple"
          value={costAnalysis.breakeven_cost_multiple === null ? "not reached" : fmtX(costAnalysis.breakeven_cost_multiple)}
        />
      </div>

      <Card title="Total cost by component (OOS trades)">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} layout="vertical" margin={{ left: 24, right: 24 }}>
            <CartesianGrid stroke="#E5E7EB" strokeDasharray="2 3" horizontal={false} />
            <XAxis type="number" tickFormatter={(v) => fmtUsd(v)} tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="name" tick={{ fontSize: 12, fill: "#1E293B" }} axisLine={false} tickLine={false} width={100} />
            <Tooltip formatter={(v: number) => fmtUsd(v)} contentStyle={{ fontSize: 12, borderRadius: 4, borderColor: "#E5E7EB" }} />
            <Bar dataKey="amount" radius={[0, 2, 2, 0]}>
              {chartData.map((_, i) => (
                <Cell key={i} fill={COLORS[i]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-3 text-sm text-muted">
          Total: <span className="num font-medium text-ink">{fmtUsd(totals.total)}</span> across {data.trades.length} OOS trades
        </div>
      </Card>
    </div>
  );
}
