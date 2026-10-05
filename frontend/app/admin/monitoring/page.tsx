"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Timer, Zap } from "lucide-react";

import { StatCard } from "@/components/stat-card";
import { Badge, badgeVariants } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { MonitoringPayload } from "@/types/advanced";

const DRIFT_BADGE: Record<string, "success" | "warning" | "danger"> = {
  NORMAL: "success",
  WARNING: "warning",
  "DRIFT DETECTED": "danger",
};

export default function AdminMonitoringPage() {
  const monitoring = useQuery({
    queryKey: ["admin-monitoring"],
    queryFn: () => apiGet<MonitoringPayload>("/admin/monitoring"),
    refetchInterval: 30_000,
  });

  if (monitoring.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-64" />
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  const data = monitoring.data;
  if (!data) {
    return <p className="p-8 text-center text-sm text-muted-foreground">Could not load monitoring data.</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Model Monitoring</h1>
        <p className="mt-1 text-sm text-muted-foreground">Prediction health, inference latency and data drift</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard title="Total Predictions" value={data.summary.total_predictions} icon={Zap} />
        <StatCard
          title="Average Predicted Score"
          value={data.summary.average_predicted_score != null ? `${data.summary.average_predicted_score}%` : "—"}
        />
        <StatCard
          title="Avg Inference Latency"
          value={data.summary.latency.avg_ms != null ? `${data.summary.latency.avg_ms} ms` : "—"}
          icon={Timer}
          hint={data.summary.latency.p95_ms != null ? `p95: ${data.summary.latency.p95_ms} ms` : undefined}
        />
      </div>

      <Card
        className={cn(
          data.drift.status === "DRIFT DETECTED" && "border-red-300",
          data.drift.status === "WARNING" && "border-amber-200",
        )}
      >
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Data & Feature Drift</CardTitle>
              <CardDescription>Population Stability Index vs the training snapshot</CardDescription>
            </div>
            <Badge className={badgeVariants({ variant: DRIFT_BADGE[data.drift.status] ?? "secondary" })}>
              {data.drift.status === "NORMAL" && <CheckCircle2 className="mr-1 h-3 w-3" />}
              {data.drift.status !== "NORMAL" && <AlertTriangle className="mr-1 h-3 w-3" />}
              {data.drift.status}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {data.drift.features.length === 0 ? (
            <p className="text-sm text-muted-foreground">{data.drift.message}</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Feature</TableHead>
                  <TableHead className="text-right">Training mean</TableHead>
                  <TableHead className="text-right">Live mean</TableHead>
                  <TableHead className="text-right">PSI</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.drift.features.map((f) => (
                  <TableRow key={f.feature}>
                    <TableCell className="font-medium">{f.feature}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{f.training_mean ?? "—"}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{f.live_mean ?? "—"}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{f.psi}</TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          "text-xs font-medium",
                          f.status === "NORMAL" ? "text-emerald-600" : f.status === "WARNING" ? "text-amber-600" : "text-red-600",
                        )}
                      >
                        {f.status}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          <p className="mt-3 text-xs text-muted-foreground">{data.drift.message}</p>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Predictions by Model Type</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {Object.entries(data.summary.predictions_by_model_type).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between">
                <span className="text-muted-foreground">{type}</span>
                <span className="font-medium">{count}</span>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Risk Distribution (all predictions)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {Object.entries(data.summary.risk_distribution).map(([level, count]) => (
              <div key={level} className="flex items-center justify-between">
                <span className="text-muted-foreground">{level}</span>
                <span className="font-medium">{count}</span>
              </div>
            ))}
            <div className="flex items-center justify-between border-t pt-2">
              <span className="text-muted-foreground">Failed batch jobs</span>
              <span className="font-medium">{data.summary.failed_batch_jobs}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
