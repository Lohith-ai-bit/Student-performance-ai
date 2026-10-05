"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, Award, CalendarCheck, Target, TrendingUp } from "lucide-react";
import Link from "next/link";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { PredictionCard } from "@/components/ai/prediction-card";
import { usePredictionHistory } from "@/components/ai/prediction-trend";
import { PredictionTrend } from "@/components/ai/prediction-trend";
import { RecommendationList } from "@/components/ai/recommendation-list";
import { RiskBadge } from "@/components/risk-badge";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { apiGet } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import type { StudentDashboard } from "@/types";
import type { ExplanationPayload, Recommendation } from "@/types/advanced";

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good Morning";
  if (hour < 17) return "Good Afternoon";
  return "Good Evening";
}

export default function StudentDashboardPage() {
  const { user } = useAuth();
  const dashboard = useQuery({
    queryKey: ["student-dashboard"],
    queryFn: () => apiGet<StudentDashboard>("/students/me/dashboard"),
  });
  const history = usePredictionHistory();
  const recommendations = useQuery({
    queryKey: ["student-recommendations"],
    queryFn: () => apiGet<Recommendation[]>("/students/me/recommendations"),
  });
  const latestPredictionId = history.data?.history[0]?.id;
  const explanation = useQuery({
    queryKey: ["explanation", latestPredictionId],
    queryFn: () => apiGet<ExplanationPayload>(`/predictions/${latestPredictionId}/explanation`),
    enabled: !!latestPredictionId,
  });

  if (dashboard.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-72" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-80" />
      </div>
    );
  }

  const data = dashboard.data;
  if (!data) {
    return (
      <Card>
        <CardContent className="p-8 text-center text-sm text-muted-foreground">
          Could not load your dashboard. Please try again later.
        </CardContent>
      </Card>
    );
  }

  const chartData = data.performance_trend.map((row) => ({
    course: row.course_code,
    previous: row.previous ?? 0,
    current: row.current ?? 0,
    predicted: row.predicted ?? 0,
  }));
  const latest = history.data?.history[0] ?? null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {greeting()}, {data.student.name ?? user?.name}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {data.student.roll_number} · {data.student.department} · Semester {data.student.semester}
          </p>
        </div>
        <Button variant="outline" asChild>
          <Link href="/student/learning">My learning progress</Link>
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard title="Current GPA" value={data.summary.gpa != null ? `${data.summary.gpa}/10` : "—"} icon={Award} hint="From completed semesters" />
        <StatCard title="Predicted Score" value={data.summary.predicted_score != null ? `${data.summary.predicted_score}%` : "—"} icon={Target} hint="AI prediction (latest)" />
        <StatCard title="Attendance" value={data.summary.attendance_percentage != null ? `${data.summary.attendance_percentage}%` : "—"} icon={CalendarCheck} />
        <StatCard title="Engagement" value={data.summary.engagement_score != null ? `${data.summary.engagement_score}` : "—"} icon={Activity} hint="Engineered engagement score" />
        <StatCard title="Risk Level" value={<RiskBadge level={data.summary.risk_level} />} icon={TrendingUp} hint="Based on latest prediction" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {latest ? (
          <PredictionCard
            predictedScore={latest.predicted_score}
            riskLevel={latest.risk_level}
            riskProbability={latest.risk_probability}
            modelName={latest.model_name}
            modelVersion={latest.model_version}
            predictionDate={latest.prediction_date}
            explanation={explanation.data}
            disclaimer={explanation.data?.disclaimer}
          />
        ) : (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center gap-2 p-10 text-center">
              <Target className="h-8 w-8 text-muted-foreground" />
              <p className="font-medium">No prediction available yet</p>
              <p className="max-w-md text-sm text-muted-foreground">
                Your faculty can generate a prediction once enough learning data is recorded.
              </p>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Performance Overview</CardTitle>
            <CardDescription>Previous, current and predicted performance per course</CardDescription>
          </CardHeader>
          <CardContent>
            {chartData.length === 0 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">
                No assessment data available yet. Add assessment data to generate a performance prediction.
              </p>
            ) : (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="course" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis domain={[0, 100]} fontSize={11} tickLine={false} axisLine={false} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="previous" name="Previous" fill="#a5b4fc" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="current" name="Current" fill="#6366f1" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="predicted" name="Predicted" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold tracking-tight">Recommended for you</h2>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/student/resources">Browse resources</Link>
          </Button>
        </div>
        {recommendations.isLoading ? (
          <Skeleton className="h-24" />
        ) : (
          <RecommendationList items={(recommendations.data ?? []).slice(0, 3)} />
        )}
      </div>

      <PredictionTrend history={history.data?.history ?? []} />
    </div>
  );
}
