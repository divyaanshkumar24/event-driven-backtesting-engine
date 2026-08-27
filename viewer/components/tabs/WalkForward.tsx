import type { BiasAudit } from "@/lib/types";
import { Card } from "../ui/Card";
import { Stat } from "../ui/Stat";
import { fmtNum, fmtPct } from "@/lib/format";

export function WalkForward({ audit }: { audit: BiasAudit }) {
  const isOos = audit.is_oos_degradation.value;
  const overfit = audit.overfitting_analysis.value;
  const regimes = audit.regime_breakdown.value;

  return (
    <div className="flex flex-col gap-4">
      <Card title="In-sample vs. out-of-sample">
        <div className="grid grid-cols-3 gap-2">
          <Stat label="IS Sharpe (avg)" value={fmtNum(isOos.is_sharpe_avg)} />
          <Stat label="OOS Sharpe" value={fmtNum(isOos.oos_sharpe)} />
          <Stat
            label="Degradation"
            value={fmtNum(isOos.degradation)}
            tone={isOos.degradation > 0 ? "neg" : "pos"}
          />
        </div>
      </Card>

      <Card title="Overfitting diagnostics">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <Stat label="Param combos / fold" value={String(overfit.n_param_combos_tested_per_fold)} />
          <Stat label="Folds" value={String(overfit.n_folds)} />
          <Stat
            label="Deflated Sharpe"
            value={fmtNum(overfit.deflated_sharpe.dsr)}
            tone={overfit.deflated_sharpe.dsr < 0.95 ? "neg" : "pos"}
          />
          <Stat
            label="PBO"
            value={overfit.pbo ? fmtPct(overfit.pbo.pbo, 0) : "n/a"}
            tone={overfit.pbo && overfit.pbo.pbo > 0.5 ? "neg" : "pos"}
          />
        </div>
        <p className="mt-3 text-xs text-muted">
          Observed Sharpe {fmtNum(overfit.deflated_sharpe.observed_sharpe)} vs. a null benchmark of{" "}
          {fmtNum(overfit.deflated_sharpe.benchmark_sharpe_under_null)} expected by chance alone across{" "}
          {overfit.deflated_sharpe.n_trials} pooled trials.
        </p>
      </Card>

      <Card title="Regime breakdown (OOS Sharpe by trailing volatility tercile)">
        {regimes ? (
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(regimes).map(([regime, sharpe]) => (
              <Stat
                key={regime}
                label={regime.replace("_", " ")}
                value={sharpe === null ? "n/a" : fmtNum(sharpe)}
                tone={sharpe === null ? "neutral" : sharpe >= 0 ? "pos" : "neg"}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-faint">{audit.regime_breakdown.explanation}</p>
        )}
      </Card>
    </div>
  );
}
