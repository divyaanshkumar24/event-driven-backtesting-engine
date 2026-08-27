"use client";

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { EquityPoint } from "@/lib/types";
import { computeDrawdownSeries } from "@/lib/derive";
import { fmtDate, fmtPct } from "@/lib/format";

export function DrawdownChart({ equity, height = 200 }: { equity: EquityPoint[]; height?: number }) {
  const data = computeDrawdownSeries(equity);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="#E5E7EB" strokeDasharray="2 3" vertical={false} />
        <XAxis
          dataKey="timestamp"
          tickFormatter={fmtDate}
          tick={{ fontSize: 11, fill: "#64748B" }}
          minTickGap={40}
          axisLine={{ stroke: "#E5E7EB" }}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(v) => fmtPct(v, 0)}
          tick={{ fontSize: 11, fill: "#64748B" }}
          axisLine={false}
          tickLine={false}
          width={48}
        />
        <Tooltip
          formatter={(value: number) => [fmtPct(value), "Drawdown"]}
          labelFormatter={(l) => fmtDate(String(l))}
          contentStyle={{ fontSize: 12, borderRadius: 4, borderColor: "#E5E7EB" }}
        />
        <Area type="monotone" dataKey="drawdown" stroke="#DC2626" fill="#FEF2F2" strokeWidth={1.25} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
