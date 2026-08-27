import type { AuditStatus } from "@/lib/types";

const COLORS: Record<AuditStatus, string> = {
  pass: "bg-pos",
  warn: "bg-warn",
  fail: "bg-neg",
  flagged: "bg-faint",
  not_applicable: "bg-line",
};

export function StatusDot({ status }: { status: AuditStatus }) {
  return <span className={`inline-block h-2 w-2 rounded-full ${COLORS[status]}`} aria-hidden />;
}
