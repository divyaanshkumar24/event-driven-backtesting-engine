import type { Manifest } from "@/lib/types";
import { fmtDate } from "@/lib/format";

export function Header({ manifest }: { manifest: Manifest }) {
  return (
    <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line pb-3">
      <div>
        <h1 className="text-xl font-semibold text-ink">
          {manifest.inputs.symbol} <span className="font-normal text-muted">— {manifest.inputs.strategy}</span>
        </h1>
        <p className="num text-xs text-faint">
          {fmtDate(manifest.inputs.data_range.start)} – {fmtDate(manifest.inputs.data_range.end)} · run{" "}
          {manifest.run_id} · engine v{manifest.engine_version}
        </p>
      </div>
      <p className="num text-xs text-faint">generated {fmtDate(manifest.timestamp)}</p>
    </header>
  );
}
