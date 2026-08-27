"use client";

import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { EquityPoint } from "@/lib/types";
import { fmtCompactUsd, fmtDate } from "@/lib/format";

const LINES: { key: keyof EquityPoint; color: string; label: string }[] = [
  { key: "net", color: "#4664e0", label: "Net" },
  { key: "gross", color: "#94A3B8", label: "Gross" },
  { key: "benchmark", color: "#DC2626", label: "Benchmark (buy & hold)" },
];

export function EquityChart({ equity, height = 320 }: { equity: EquityPoint[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={equity} margin={{ top: 4, right: 12, bottom: 0, left: 0 }}>
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
          tickFormatter={(v) => fmtCompactUsd(v)}
          tick={{ fontSize: 11, fill: "#64748B" }}
          axisLine={false}
          tickLine={false}
          width={56}
        />
        <Tooltip
          formatter={(value: number, name: string) => [fmtCompactUsd(value), name]}
          labelFormatter={(l) => fmtDate(String(l))}
          contentStyle={{ fontSize: 12, borderRadius: 4, borderColor: "#E5E7EB" }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {LINES.map((l) => (
          <Line
            key={l.key}
            type="monotone"
            dataKey={l.key}
            name={l.label}
            stroke={l.color}
            dot={false}
            strokeWidth={l.key === "net" ? 2 : 1.25}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
