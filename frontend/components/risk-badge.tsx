import type { RiskLevel } from "@/types";

import { Badge } from "@/components/ui/badge";

const RISK_STYLES: Record<RiskLevel, { variant: "success" | "warning" | "danger" | "critical"; label: string }> = {
  LOW: { variant: "success", label: "Low Risk" },
  MEDIUM: { variant: "warning", label: "Medium Risk" },
  HIGH: { variant: "danger", label: "High Risk" },
  CRITICAL: { variant: "critical", label: "Critical" },
};

export function RiskBadge({ level }: { level: RiskLevel | string | null | undefined }) {
  if (!level) return <Badge variant="outline">No prediction</Badge>;
  const style = RISK_STYLES[level as RiskLevel] ?? { variant: "secondary" as const, label: level };
  return <Badge variant={style.variant}>{style.label}</Badge>;
}
