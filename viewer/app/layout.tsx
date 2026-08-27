import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Backtest Report",
  description: "Point-in-time-safe backtest report viewer",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans">{children}</body>
    </html>
  );
}
