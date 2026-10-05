"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Rocket } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet, apiPost } from "@/lib/api";
import type { ModelVersionRecord } from "@/types/advanced";

const STATUS_BADGE = (status: string) =>
  status === "PRODUCTION" ? "success" : status === "VALIDATED" ? "default" : status === "FAILED" ? "danger" : ("secondary" as const);

export default function AdminModelsPage() {
  const queryClient = useQueryClient();
  const registry = useQuery({
    queryKey: ["model-registry"],
    queryFn: () => apiPost<ModelVersionRecord[]>("/ml/registry/sync", {}),
  });

  const promote = useMutation({
    mutationFn: (id: string) => apiPost<ModelVersionRecord>(`/ml/registry/${id}/promote`, {}),
    onSuccess: () => {
      toast.success("Model promoted to production");
      queryClient.invalidateQueries({ queryKey: ["model-registry"] });
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Model Registry</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Versioned models with real metrics. Only validated models can be promoted to production.
        </p>
      </div>

      <Card>
        <CardContent className="p-0">
          {registry.isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Model</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Version</TableHead>
                  <TableHead>Trained</TableHead>
                  <TableHead>Key metrics</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="w-24" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {(registry.data ?? []).map((m) => (
                  <TableRow key={m.id}>
                    <TableCell className="font-medium">{m.model_name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{m.model_type}</Badge>
                    </TableCell>
                    <TableCell>{m.version}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(m.training_date).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="max-w-56 truncate font-mono text-xs text-muted-foreground">
                      {JSON.stringify(m.metrics)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={STATUS_BADGE(m.status)}>{m.status}</Badge>
                    </TableCell>
                    <TableCell>
                      {m.status === "VALIDATED" && (
                        <Button size="sm" variant="outline" onClick={() => promote.mutate(m.id)} disabled={promote.isPending}>
                          <Rocket /> Promote
                        </Button>
                      )}
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
