"use client";

import { TrendingDown, TrendingUp } from "lucide-react";

import { cn } from "@/lib/utils";
import type { ExplanationFactor } from "@/types/advanced";

export function FactorList({ factors, max = 6 }: { factors: ExplanationFactor[]; max?: number }) {
  const list = factors.slice(0, max);
  if (list.length === 0) {
    return <p className="text-sm text-muted-foreground">No explanation factors available.</p>;
  }
  const maxAbs = Math.max(...list.map((f) => Math.abs(f.importance)), 0.0001);
  return (
    <ul className="space-y-2">
      {list.map((factor) => (
        <li key={factor.feature + factor.direction} className="space-y-1">
          <div className="flex items-center justify-between gap-2 text-sm">
            <span className="flex items-center gap-1.5">
              {factor.direction === "positive" ? (
                <TrendingUp className="h-3.5 w-3.5 text-emerald-600" />
              ) : (
                <TrendingDown className="h-3.5 w-3.5 text-red-500" />
              )}
              {factor.label}
            </span>
            <span className={cn("font-mono text-xs", factor.direction === "positive" ? "text-emerald-600" : "text-red-500")}>
              {factor.importance > 0 ? "+" : ""}
              {factor.importance.toFixed(3)}
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
            <div
              className={cn("h-full rounded-full", factor.direction === "positive" ? "bg-emerald-500" : "bg-red-400")}
              style={{ width: `${(Math.abs(factor.importance) / maxAbs) * 100}%` }}
            />
          </div>
          {factor.explanation_text && <p className="text-xs text-muted-foreground">{factor.explanation_text}</p>}
        </li>
      ))}
    </ul>
  );
}
