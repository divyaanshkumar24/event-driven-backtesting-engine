import type { BundleData } from "@/lib/types";
import { Card } from "../ui/Card";
import { EquityChart } from "../EquityChart";
import { fmtDate, fmtPct, fmtUsd } from "@/lib/format";

export function Overview({ data }: { data: BundleData }) {
  const { manifest } = data;
  const wf = manifest.inputs.walkforward_config;
  const cm = manifest.inputs.cost_model;

  return (
    <div className="flex flex-col gap-4">
      <Card title="Equity">
        <EquityChart equity={data.equity} height={280} />
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card title="Universe & Strategy">
          <dl className="flex flex-col gap-1.5 text-sm">
            <Row k="Symbol" v={manifest.inputs.symbol} />
            <Row k="Strategy" v={manifest.inputs.strategy} />
            <Row k="Data range" v={`${fmtDate(manifest.inputs.data_range.start)} – ${fmtDate(manifest.inputs.data_range.end)}`} />
            <Row k="Initial cash" v={fmtUsd(manifest.inputs.initial_cash)} />
            <Row k="Param grid" v={Object.entries(manifest.inputs.param_grid).map(([k, v]) => `${k}: [${v.join(", ")}]`).join(" · ")} />
          </dl>
        </Card>

        <Card title="Walk-Forward Config">
          <dl className="flex flex-col gap-1.5 text-sm">
            <Row k="Mode" v={wf.mode} />
            <Row k="Train bars" v={String(wf.train_bars)} />
            <Row k="Test bars" v={String(wf.test_bars)} />
            <Row k="Purge bars" v={String(wf.purge_bars)} />
            <Row k="Embargo bars" v={String(wf.embargo_bars)} />
          </dl>
        </Card>

        <Card title="Cost Model">
          <dl className="flex flex-col gap-1.5 text-sm">
            <Row k="Commission" v={`${cm.commission.mode} $${cm.commission.per_share}/sh`} />
            <Row k="Half-spread" v={`${cm.spread.half_spread_bps} bps`} />
            <Row k="Impact coefficient" v={String(cm.impact.y)} />
            <Row k="Impact lookback" v={`${cm.impact_lookback} bars`} />
            <Row k="Annualized cost drag" v={fmtPct((data.biasAudit.cost_analysis.value as any).annualized_cost_drag)} />
          </dl>
        </Card>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-muted">{k}</dt>
      <dd className="num text-right text-ink">{v}</dd>
    </div>
  );
}
