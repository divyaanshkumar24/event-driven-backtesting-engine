import type { Trade } from "@/lib/types";
import { Card } from "../ui/Card";
import { fmtDate, fmtNum, fmtUsd } from "@/lib/format";

export function Trades({ trades }: { trades: Trade[] }) {
  return (
    <Card title={`Trade blotter (${trades.length} fills)`} className="overflow-hidden p-0">
      <div className="max-h-[560px] overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-panel">
            <tr className="border-b border-line">
              <Th align="left">Date</Th>
              <Th align="left">Symbol</Th>
              <Th align="right">Qty</Th>
              <Th align="right">Fill Price</Th>
              <Th align="right">Notional</Th>
              <Th align="right">Commission</Th>
              <Th align="right">Half-Spread</Th>
              <Th align="right">Impact</Th>
              <Th align="right">Total Cost</Th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t, i) => {
              const totalCost = t.commission + t.half_spread + t.impact;
              const notional = Math.abs(t.quantity * t.fill_price);
              return (
                <tr key={i} className="border-b border-line last:border-0 hover:bg-accent-soft/40">
                  <Td>{fmtDate(t.timestamp)}</Td>
                  <Td>{t.symbol}</Td>
                  <Td align="right" tone={t.quantity >= 0 ? "pos" : "neg"}>
                    {t.quantity >= 0 ? "+" : ""}
                    {fmtNum(t.quantity, 0)}
                  </Td>
                  <Td align="right">{fmtUsd(t.fill_price, 2)}</Td>
                  <Td align="right">{fmtUsd(notional)}</Td>
                  <Td align="right">{fmtUsd(t.commission, 2)}</Td>
                  <Td align="right">{fmtUsd(t.half_spread, 2)}</Td>
                  <Td align="right">{fmtUsd(t.impact, 2)}</Td>
                  <Td align="right">{fmtUsd(totalCost, 2)}</Td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function Th({ children, align = "left" }: { children: React.ReactNode; align?: "left" | "right" }) {
  return (
    <th className={`label-caps px-3 py-2 text-micro font-semibold text-muted ${align === "right" ? "text-right" : "text-left"}`}>
      {children}
    </th>
  );
}

function Td({
  children,
  align = "left",
  tone = "neutral",
}: {
  children: React.ReactNode;
  align?: "left" | "right";
  tone?: "neutral" | "pos" | "neg";
}) {
  const toneClass = tone === "pos" ? "text-pos" : tone === "neg" ? "text-neg" : "text-ink";
  return (
    <td className={`num px-3 py-1.5 ${align === "right" ? "text-right" : "text-left"} ${toneClass}`}>{children}</td>
  );
}
