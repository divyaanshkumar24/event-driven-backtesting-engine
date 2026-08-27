export interface Manifest {
  run_id: string;
  timestamp: string;
  engine_version: string;
  data_hash: string;
  inputs: {
    symbol: string;
    fetch_start: string;
    data_range: { start: string; end: string };
    strategy: string;
    param_grid: Record<string, number[]>;
    walkforward_config: {
      mode: string;
      train_bars: number;
      test_bars: number;
      purge_bars: number;
      embargo_bars: number;
    };
    cost_model: {
      commission: { mode: string; per_share: number; per_trade: number; bps: number };
      spread: { half_spread_bps: number };
      impact: { y: number };
      impact_lookback: number;
    };
    initial_cash: number;
  };
}

export interface Metrics {
  cagr: number;
  sharpe: number;
  sortino: number;
  calmar: number;
  max_drawdown: number;
  max_drawdown_duration: { bars: number; censored: boolean };
  hit_rate: number | null;
  avg_win: number | null;
  avg_loss: number | null;
  exposure: number;
  turnover: number;
  deflated_sharpe: {
    dsr: number;
    observed_sharpe: number;
    benchmark_sharpe_under_null: number;
    n_trials: number;
    n_obs: number;
  };
  gross_vs_net: {
    gross_cagr: number;
    net_cagr: number;
    gross_sharpe: number;
    net_sharpe: number;
  };
}

export type AuditStatus = "pass" | "warn" | "fail" | "flagged" | "not_applicable";

export interface AuditField {
  status: AuditStatus;
  value: unknown;
  explanation: string;
}

export interface BiasAudit {
  look_ahead_violations: AuditField;
  fill_timing_assumption: AuditField;
  survivorship_posture: AuditField;
  cost_analysis: AuditField & {
    value: {
      gross_sharpe: number;
      net_sharpe: number;
      annualized_cost_drag: number;
      breakeven_cost_multiple: number | null;
    };
  };
  turnover: AuditField & { value: number };
  overfitting_analysis: AuditField & {
    value: {
      n_param_combos_tested_per_fold: number;
      n_folds: number;
      deflated_sharpe: Metrics["deflated_sharpe"];
      pbo: { pbo: number; n_combinations: number; mean_logit: number; n_splits: number } | null;
    };
  };
  is_oos_degradation: AuditField & {
    value: { is_sharpe_avg: number; oos_sharpe: number; degradation: number };
  };
  regime_breakdown: AuditField & { value: Record<string, number | null> | null };
  capacity: AuditField & { value: number | null };
}

export interface ParamSensitivityPoint {
  params: Record<string, number>;
  sharpe: number;
}

export interface RebalanceSensitivityPoint {
  every_n_bars: number;
  sharpe: number;
}

export interface Sensitivity {
  param_grid: ParamSensitivityPoint[];
  rebalance_frequency: RebalanceSensitivityPoint[];
  reference_params_used_for_rebalance_sweep: Record<string, number>;
}

export interface EquityPoint {
  timestamp: string;
  net: number;
  gross: number;
  benchmark: number;
}

export interface Trade {
  timestamp: string;
  symbol: string;
  quantity: number;
  fill_price: number;
  commission: number;
  half_spread: number;
  impact: number;
}

export interface BundleData {
  manifest: Manifest;
  metrics: Metrics;
  sensitivity: Sensitivity;
  biasAudit: BiasAudit;
  equity: EquityPoint[];
  trades: Trade[];
}
