"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, BookOpen, CheckCircle2, ClipboardCheck, Flame } from "lucide-react";

import { RecommendationList } from "@/components/ai/recommendation-list";
import { StatCard } from "@/components/stat-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { apiGet } from "@/lib/api";
import type { LearningProgress, Recommendation } from "@/types/advanced";

export default function StudentLearningPage() {
  const progress = useQuery({
    queryKey: ["learning-progress"],
    queryFn: () => apiGet<LearningProgress>("/students/me/learning-progress"),
  });
  const recommendations = useQuery({
    queryKey: ["student-recommendations"],
    queryFn: () => apiGet<Recommendation[]>("/students/me/recommendations"),
  });

  if (progress.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-64" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      </div>
    );
  }

  const data = progress.data;
  const completionRate =
    data && data.recommendations_total > 0
      ? Math.round((data.recommendations_completed / data.recommendations_total) * 100)
      : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">My Learning</h1>
        <p className="mt-1 text-sm text-muted-foreground">Your learning hours, practice activity and plan progress</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Learning Hours" value={data?.learning_hours ?? "—"} icon={Flame} hint="Total recorded study sessions" />
        <StatCard title="Practice Questions" value={data?.practice_questions ?? "—"} icon={ClipboardCheck} />
        <StatCard title="Recommendations Completed" value={data?.recommendations_completed ?? "—"} icon={CheckCircle2} />
        <StatCard title="Recommendations In Progress" value={data?.recommendations_in_progress ?? "—"} icon={Activity} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Learning Plan Progress</CardTitle>
          <CardDescription>Share of your personalized recommendations completed</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <Progress value={completionRate} />
          <p className="text-sm text-muted-foreground">
            {completionRate}% complete ({data?.recommendations_completed ?? 0} of {data?.recommendations_total ?? 0})
          </p>
        </CardContent>
      </Card>

      <div>
        <h2 className="mb-3 text-lg font-semibold tracking-tight">Your personalized learning plan</h2>
        {recommendations.isLoading ? (
          <Skeleton className="h-24" />
        ) : (
          <RecommendationList items={recommendations.data ?? []} />
        )}
      </div>
    </div>
  );
}
