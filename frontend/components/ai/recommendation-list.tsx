"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BookOpen, CalendarCheck, CheckCircle2, ClipboardCheck, Clock, ExternalLink, ThumbsUp, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { apiPatch, apiPost } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Recommendation } from "@/types/advanced";

const TYPE_ICONS: Record<string, typeof BookOpen> = {
  CONTENT: BookOpen,
  PRACTICE: ClipboardCheck,
  REVISION: BookOpen,
  ATTENDANCE: CalendarCheck,
  TIME_MANAGEMENT: Clock,
  ASSESSMENT: ClipboardCheck,
  FACULTY_INTERVENTION: CalendarCheck,
};

const PRIORITY_BADGE = (priority: number) =>
  priority <= 2 ? "danger" : priority === 3 ? "warning" : ("secondary" as const);

export function RecommendationCard({ item, onUpdated }: { item: Recommendation; onUpdated?: () => void }) {
  const queryClient = useQueryClient();
  const [showFeedback, setShowFeedback] = useState(false);
  const [rating, setRating] = useState(4);
  const [helpful, setHelpful] = useState(true);

  const update = useMutation({
    mutationFn: (status: string) => apiPatch(`/recommendations/${item.id}`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["student-recommendations"] });
      queryClient.invalidateQueries({ queryKey: ["learning-progress"] });
      toast.success("Recommendation updated");
      onUpdated?.();
    },
    onError: (e) => toast.error(e.message),
  });

  const sendFeedback = useMutation({
    mutationFn: () =>
      apiPost(`/recommendations/${item.id}/feedback`, { rating, helpful, feedback_text: null }),
    onSuccess: () => {
      toast.success("Thanks for the feedback!");
      setShowFeedback(false);
    },
    onError: (e) => toast.error(e.message),
  });

  const Icon = TYPE_ICONS[item.recommendation_type] ?? BookOpen;

  return (
    <Card className={cn(item.status === "COMPLETED" && "opacity-70")}>
      <CardContent className="space-y-2 p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <Icon className="h-4 w-4" />
            </span>
            <div>
              <p className="font-medium leading-tight">{item.title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{item.description}</p>
              <p className="mt-1 text-xs text-muted-foreground">Reason: {item.reason}</p>
            </div>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1">
            <Badge variant={PRIORITY_BADGE(item.priority)}>P{item.priority}</Badge>
            <Badge variant="outline">{item.status}</Badge>
          </div>
        </div>

        {item.status !== "COMPLETED" && item.status !== "DISMISSED" && (
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Button size="sm" variant="outline" onClick={() => update.mutate("IN_PROGRESS")} disabled={update.isPending}>
              Start
            </Button>
            <Button size="sm" onClick={() => update.mutate("COMPLETED")} disabled={update.isPending}>
              <CheckCircle2 /> Mark complete
            </Button>
            <Button size="sm" variant="ghost" onClick={() => update.mutate("DISMISSED")} disabled={update.isPending}>
              <X /> Dismiss
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setShowFeedback((v) => !v)}>
              <ThumbsUp /> Feedback
            </Button>
          </div>
        )}

        {showFeedback && (
          <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-muted/30 p-3">
            <label className="flex items-center gap-2 text-sm">
              Rating
              <select
                className="rounded-md border bg-card px-2 py-1 text-sm"
                value={rating}
                onChange={(e) => setRating(Number(e.target.value))}
              >
                {[5, 4, 3, 2, 1].map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="radio" checked={helpful} onChange={() => setHelpful(true)} /> Helpful
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="radio" checked={!helpful} onChange={() => setHelpful(false)} /> Not helpful
            </label>
            <Button size="sm" onClick={() => sendFeedback.mutate()} disabled={sendFeedback.isPending}>
              Send
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function RecommendationList({ items }: { items: Recommendation[] }) {
  if (items.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="p-8 text-center text-sm text-muted-foreground">
          No recommendations yet. Generate a prediction to receive personalized suggestions.
        </CardContent>
      </Card>
    );
  }
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <RecommendationCard key={item.id} item={item} />
      ))}
    </div>
  );
}
