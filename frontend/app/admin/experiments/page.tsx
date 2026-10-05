"use client";

import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet } from "@/lib/api";
import type { ExperimentRecord } from "@/types/advanced";

function metricOf(exp: ExperimentRecord, key: string, split: "validation" | "test" = "test"): number | null {
  const nested = exp.metrics?.[split]?.[key];
  if (typeof nested === "number") return nested;
  const flat = exp.metrics?.[split];
  if (flat && typeof (flat as Record<string, number>)[key] === "number") return (flat as Record<string, number>)[key];
  return null;
}

export default function AdminExperimentsPage() {
  const experiments = useQuery({
    queryKey: ["experiments"],
    queryFn: () => apiGet<ExperimentRecord[]>("/ml/experiments"),
  });

  const data = experiments.data ?? [];
  const comparison = data
    .filter((e) => metricOf(e, "RMSE") !== null)
    .map((e) => ({
      name: e.experiment_name.split("/").pop()!.slice(0, 18),
      rmse: metricOf(e, "RMSE") as number,
      f1: metricOf(e, "F1") ?? 0,
    }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Experiments</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          ML vs Transformer vs Hybrid + ablation studies. Every number is an actual experiment result.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Test RMSE by model (lower is better)</CardTitle>
          <CardDescription>Regression task · same 70/15/15 split for all models</CardDescription>
        </CardHeader>
        <CardContent className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={comparison} layout="vertical" margin={{ left: 24 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
              <XAxis type="number" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="name" width={130} fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip />
              <Bar dataKey="rmse" name="Test RMSE" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Experiment comparison table</CardTitle>
          <CardDescription>All recorded experiments with validation and test metrics</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {experiments.isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Experiment</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Test RMSE</TableHead>
                  <TableHead className="text-right">Test R²</TableHead>
                  <TableHead className="text-right">Test MAE</TableHead>
                  <TableHead className="text-right">Test F1</TableHead>
                  <TableHead className="text-right">ROC-AUC</TableHead>
                  <TableHead className="text-right">Duration</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((e) => (
                  <TableRow key={e.id}>
                    <TableCell>
                      <p className="font-medium">{e.experiment_name}</p>
                      {e.notes && <p className="text-xs text-muted-foreground">{e.notes}</p>}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{e.model_type}</Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">{metricOf(e, "RMSE") ?? "—"}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{metricOf(e, "R2") ?? "—"}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{metricOf(e, "MAE") ?? "—"}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{metricOf(e, "F1") ?? "—"}</TableCell>
                    <TableCell className="text-right font-mono text-xs">{metricOf(e, "ROC_AUC") ?? "—"}</TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {e.training_duration_seconds ? `${e.training_duration_seconds.toFixed(0)}s` : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
