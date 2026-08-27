"use client";

import { useEffect, useState } from "react";
import type { BundleData } from "./types";

interface State {
  data: BundleData | null;
  error: string | null;
  loading: boolean;
}

/** Static-export viewer, no backend: this fetches plain JSON files copied
 * into public/data/current/ at export time (see engine/bundle/viewer_export.py).
 * Works identically served from Vercel static hosting, a plain S3 bucket,
 * or `next dev`.
 */
export function useBundleData(): State {
  const [state, setState] = useState<State>({ data: null, error: null, loading: true });

  useEffect(() => {
    let cancelled = false;
    const base = `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}/data/current`;

    const fetchJson = (name: string) =>
      fetch(`${base}/${name}`).then((r) => {
        if (!r.ok) throw new Error(`failed to load ${name}: ${r.status}`);
        return r.json();
      });

    Promise.all([
      fetchJson("manifest.json"),
      fetchJson("metrics.json"),
      fetchJson("sensitivity.json"),
      fetchJson("bias_audit.json"),
      fetchJson("equity.json"),
      fetchJson("trades.json"),
    ])
      .then(([manifest, metrics, sensitivity, biasAudit, equity, trades]) => {
        if (cancelled) return;
        setState({ data: { manifest, metrics, sensitivity, biasAudit, equity, trades }, error: null, loading: false });
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setState({ data: null, error: e instanceof Error ? e.message : String(e), loading: false });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
