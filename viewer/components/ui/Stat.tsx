export function Stat({
  label,
  value,
  tone = "neutral",
  sub,
}: {
  label: string;
  value: string;
  tone?: "neutral" | "pos" | "neg";
  sub?: string;
}) {
  const toneClass = tone === "pos" ? "text-pos" : tone === "neg" ? "text-neg" : "text-ink";
  return (
    <div className="flex flex-col gap-0.5 border border-line bg-panel px-3 py-2">
      <span className="label-caps text-micro text-muted">{label}</span>
      <span className={`num text-lg font-semibold leading-tight ${toneClass}`}>{value}</span>
      {sub ? <span className="num text-micro text-faint">{sub}</span> : null}
    </div>
  );
}
