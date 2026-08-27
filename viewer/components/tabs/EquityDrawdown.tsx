import type { BundleData } from "@/lib/types";
import { Card } from "../ui/Card";
import { EquityChart } from "../EquityChart";
import { DrawdownChart } from "../DrawdownChart";

export function EquityDrawdown({ data }: { data: BundleData }) {
  return (
    <div className="flex flex-col gap-4">
      <Card title="Equity — gross vs net vs benchmark">
        <EquityChart equity={data.equity} height={340} />
      </Card>
      <Card title="Drawdown (net)">
        <DrawdownChart equity={data.equity} height={220} />
      </Card>
    </div>
  );
}
