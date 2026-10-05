"use client";

import { useQuery } from "@tanstack/react-query";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiGet } from "@/lib/api";
import type { PredictionRecord } from "@/types";

export function PredictionTrend({ history, title = "Prediction Trend" }: { history: PredictionRecord[]; title?: string }) {
  const ordered = [...history].sort(
    (a, b) => new Date(a.prediction_date).getTime() - new Date(b.prediction_date).getTime(),
  );
  const data = ordered.map((h) => ({
    date: new Date(h.prediction_date).toLocaleDateString(),
    score: h.predicted_score,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>Historical and current predictions, oldest to newest</CardDescription>
      </CardHeader>
      <CardContent>
        {data.length < 2 ? (
          <p className="py-10 text-center text-sm text-muted-foreground">
            Not enough predictions yet to draw a trend.
          </p>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis domain={[0, 100]} fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip />
                <Line type="monotone" dataKey="score" name="Predicted score" stroke="#6366f1" strokeWidth={2} dot />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function usePredictionHistory(enabled = true) {
  return useQuery({
    queryKey: ["student-prediction-history"],
    queryFn: () => apiGet<{ success: boolean; history: PredictionRecord[] }>("/students/me/predictions/history"),
    enabled,
  });
}
