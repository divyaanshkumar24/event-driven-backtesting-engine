"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ParamSensitivityPoint, Sensitivity as SensitivityData } from "@/lib/types";
import { Card } from "../ui/Card";
import { fmtNum } from "@/lib/format";

const HEAT_COLORS = ["#FEE2E2", "#FEF3C7", "#F1F5F9", "#DCFCE7", "#BBF7D0"];

function bucketColor(value: number, min: number, max: number): string {
  if (max === min) return HEAT_COLORS[2];
  const t = (value - min) / (max - min);
  const idx = Math.min(4, Math.max(0, Math.floor(t * 5)));
  return HEAT_COLORS[idx];
}

function buildGrid(points: ParamSensitivityPoint[]) {
  const keys = Object.keys(points[0]?.params ?? {});
  if (keys.length !== 2) return null;
  const [rowKey, colKey] = keys;
  const rows = Array.from(new Set(points.map((p) => p.params[rowKey]))).sort((a, b) => a - b);
  const cols = Array.from(new Set(points.map((p) => p.params[colKey]))).sort((a, b) => a - b);
  const cell = new Map<string, number>();
  for (const p of points) cell.set(`${p.params[rowKey]}:${p.params[colKey]}`, p.sharpe);
  const sharpes = points.map((p) => p.sharpe);
  return { rowKey, colKey, rows, cols, cell, min: Math.min(...sharpes), max: Math.max(...sharpes) };
}

function ParamHeatmap({ points }: { points: ParamSensitivityPoint[] }) {
  const grid = buildGrid(points);
  if (!grid) {
    return (
      <table className="w-full text-sm">
        <tbody>
          {points.map((p, i) => (
            <tr key={i} className="border-b border-line last:border-0">
              <td className="num py-1 text-muted">{JSON.stringify(p.params)}</td>
              <td className="num py-1 text-right font-medium">{fmtNum(p.sharpe)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }
  const { rowKey, colKey, rows, cols, cell, min, max } = grid;
  return (
    <div className="overflow-x-auto">
      <table className="border-collapse text-sm">
        <thead>
          <tr>
            <th className="label-caps px-2 py-1 text-left text-micro text-muted">
              {rowKey} \ {colKey}
            </th>
            {cols.map((c) => (
              <th key={c} className="num px-2 py-1 text-center text-xs font-medium text-muted">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r}>
              <th className="num px-2 py-1 text-left text-xs font-medium text-muted">{r}</th>
              {cols.map((c) => {
                const v = cell.get(`${r}:${c}`);
                return (
                  <td
                    key={c}
                    className="num border border-line px-3 py-1.5 text-center text-xs font-medium text-ink"
                    style={{ background: v === undefined ? "transparent" : bucketColor(v, min, max) }}
                  >
                    {v === undefined ? "—" : fmtNum(v)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Sensitivity({ sensitivity }: { sensitivity: SensitivityData }) {
  return (
    <div className="flex flex-col gap-4">
      <Card title="Sharpe vs. parameter grid">
        <ParamHeatmap points={sensitivity.param_grid} />
      </Card>

      <Card title="Sharpe vs. rebalance frequency">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={sensitivity.rebalance_frequency} margin={{ top: 4, right: 12, left: 0 }}>
            <CartesianGrid stroke="#E5E7EB" strokeDasharray="2 3" vertical={false} />
            <XAxis
              dataKey="every_n_bars"
              tickFormatter={(v) => `every ${v}`}
              tick={{ fontSize: 11, fill: "#64748B" }}
              axisLine={{ stroke: "#E5E7EB" }}
              tickLine={false}
            />
            <YAxis tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} width={40} />
            <Tooltip formatter={(v: number) => fmtNum(v)} contentStyle={{ fontSize: 12, borderRadius: 4, borderColor: "#E5E7EB" }} />
            <Bar dataKey="sharpe" fill="#4664e0" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-2 text-xs text-muted">
          Reference params: <span className="num">{JSON.stringify(sensitivity.reference_params_used_for_rebalance_sweep)}</span>
        </div>
      </Card>
    </div>
  );
}
