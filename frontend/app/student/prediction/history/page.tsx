"use client";

import { useQuery } from "@tanstack/react-query";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet } from "@/lib/api";
import type { PredictionRecord } from "@/types";

export default function StudentPredictionHistoryPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["student-prediction-history"],
    queryFn: () => apiGet<{ success: boolean; history: PredictionRecord[] }>("/students/me/predictions/history"),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-72" />
      </div>
    );
  }

  const history = [...(data?.history ?? [])].sort(
    (a, b) => new Date(a.prediction_date).getTime() - new Date(b.prediction_date).getTime(),
  );
  const chartData = history.map((h) => ({
    date: new Date(h.prediction_date).toLocaleDateString(),
    score: h.predicted_score,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Prediction History</h1>
        <p className="mt-1 text-sm text-muted-foreground">How your predicted performance evolves over time</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Predicted Score Over Time</CardTitle>
          <CardDescription>Every stored prediction, oldest to newest</CardDescription>
        </CardHeader>
        <CardContent>
          {chartData.length < 2 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              Not enough predictions yet to draw a trend. Generate more predictions to see progress over time.
            </p>
          ) : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis domain={[0, 100]} fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip />
                  <Line type="monotone" dataKey="score" name="Predicted score" stroke="#6366f1" strokeWidth={2} dot />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>All Predictions</CardTitle>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No predictions stored yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead className="text-right">Predicted Score</TableHead>
                  <TableHead className="text-right">Risk Probability</TableHead>
                  <TableHead>Risk</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {[...(data?.history ?? [])].map((h) => (
                  <TableRow key={h.id}>
                    <TableCell>{new Date(h.prediction_date).toLocaleString()}</TableCell>
                    <TableCell>
                      {h.model_name} v{h.model_version}
                    </TableCell>
                    <TableCell className="text-right font-medium">{h.predicted_score.toFixed(1)}%</TableCell>
                    <TableCell className="text-right">{(h.risk_probability * 100).toFixed(1)}%</TableCell>
                    <TableCell>{h.risk_level}</TableCell>
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
