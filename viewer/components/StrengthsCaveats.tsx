"use client";

import { motion } from "framer-motion";
import type { AuditField, AuditStatus, BiasAudit } from "@/lib/types";
import { fmtCompactUsd, fmtPct, fmtX } from "@/lib/format";

const FIELD_LABELS: Record<keyof BiasAudit, string> = {
  look_ahead_violations: "Look-ahead violations",
  fill_timing_assumption: "Fill timing assumption",
  survivorship_posture: "Survivorship posture",
  cost_analysis: "Gross vs net cost impact",
  turnover: "Turnover",
  overfitting_analysis: "Overfitting risk (DSR / PBO)",
  is_oos_degradation: "In-sample vs out-of-sample",
  regime_breakdown: "Regime breakdown",
  capacity: "Capacity",
};

function summarize(key: keyof BiasAudit, field: AuditField): string {
  const v = field.value as any; // eslint-disable-line @typescript-eslint/no-explicit-any
  switch (key) {
    case "look_ahead_violations":
      return `${v} violations found`;
    case "fill_timing_assumption":
      return String(v);
    case "survivorship_posture":
      return String(v).replace(/-/g, " ");
    case "cost_analysis":
      return `net Sharpe ${v.net_sharpe.toFixed(2)} vs gross ${v.gross_sharpe.toFixed(2)} — ${fmtPct(v.annualized_cost_drag)} annual drag`;
    case "turnover":
      return `${fmtX(v)} of average equity`;
    case "overfitting_analysis": {
      const dsr = v.deflated_sharpe.dsr.toFixed(2);
      const pbo = v.pbo ? fmtPct(v.pbo.pbo, 0) : "n/a";
      return `Deflated Sharpe ${dsr}, PBO ${pbo} across ${v.n_param_combos_tested_per_fold * v.n_folds} trials`;
    }
    case "is_oos_degradation":
      return `IS ${v.is_sharpe_avg.toFixed(2)} → OOS ${v.oos_sharpe.toFixed(2)}`;
    case "regime_breakdown":
      if (!v) return "not enough data to bucket into regimes";
      return Object.entries(v)
        .map(([k, s]) => `${k.replace("_", " ")}: ${s === null ? "n/a" : (s as number).toFixed(2)}`)
        .join(" · ");
    case "capacity":
      return v === null ? "not reached within tested AUM range" : `~${fmtCompactUsd(v)} before impact erodes returns`;
    default:
      return "";
  }
}

const BUCKET_META: Record<"strength" | "caveat" | "note", { title: string; dot: string; text: string }> = {
  strength: { title: "Strengths", dot: "bg-pos", text: "text-pos" },
  caveat: { title: "Caveats", dot: "bg-neg", text: "text-neg" },
  note: { title: "Notes", dot: "bg-faint", text: "text-muted" },
};

function bucketOf(status: AuditStatus): "strength" | "caveat" | "note" {
  if (status === "pass") return "strength";
  if (status === "warn" || status === "fail") return "caveat";
  return "note";
}

export function StrengthsCaveats({ audit }: { audit: BiasAudit }) {
  const entries = Object.entries(audit) as [keyof BiasAudit, AuditField][];
  const buckets: Record<"strength" | "caveat" | "note", [keyof BiasAudit, AuditField][]> = {
    strength: [],
    caveat: [],
    note: [],
  };
  for (const [key, field] of entries) buckets[bucketOf(field.status)].push([key, field]);

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      {(["strength", "caveat", "note"] as const).map((bucket) => {
        const meta = BUCKET_META[bucket];
        const items = buckets[bucket];
        return (
          <motion.div
            key={bucket}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="rounded border border-line bg-panel"
          >
            <div className="border-b border-line px-4 py-2">
              <h3 className={`label-caps text-xs font-semibold ${meta.text}`}>
                {meta.title} ({items.length})
              </h3>
            </div>
            <ul className="divide-y divide-line">
              {items.length === 0 ? (
                <li className="px-4 py-3 text-sm text-faint">None</li>
              ) : (
                items.map(([key, field]) => (
                  <li key={key} className="flex gap-2 px-4 py-2.5" title={field.explanation}>
                    <span className={`mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full ${meta.dot}`} aria-hidden />
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-ink">{FIELD_LABELS[key]}</div>
                      <div className="num text-xs text-muted">{summarize(key, field)}</div>
                    </div>
                  </li>
                ))
              )}
            </ul>
          </motion.div>
        );
      })}
    </div>
  );
}
