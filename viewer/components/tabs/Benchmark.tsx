import type { EquityPoint } from "@/lib/types";
import { Card } from "../ui/Card";
import { Stat } from "../ui/Stat";
import { EquityChart } from "../EquityChart";
import { fmtPct } from "@/lib/format";

export function Benchmark({ equity, symbol }: { equity: EquityPoint[]; symbol: string }) {
  const first = equity[0];
  const last = equity[equity.length - 1];
  const netReturn = first ? last.net / first.net - 1 : 0;
  const benchmarkReturn = first ? last.benchmark / first.benchmark - 1 : 0;
  const delta = netReturn - benchmarkReturn;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-3 gap-2">
        <Stat label="Strategy (net) return" value={fmtPct(netReturn)} tone={netReturn >= 0 ? "pos" : "neg"} />
        <Stat label={`Buy & hold ${symbol}`} value={fmtPct(benchmarkReturn)} tone={benchmarkReturn >= 0 ? "pos" : "neg"} />
        <Stat label="Excess return" value={fmtPct(delta)} tone={delta >= 0 ? "pos" : "neg"} />
      </div>
      <Card title={`Net equity vs. buy-and-hold ${symbol}`}>
        <EquityChart equity={equity} height={320} />
      </Card>
    </div>
  );
}
