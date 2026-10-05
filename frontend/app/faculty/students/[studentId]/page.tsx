"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { FactorList } from "@/components/ai/factor-list";
import { RecommendationList } from "@/components/ai/recommendation-list";
import { RiskBadge } from "@/components/risk-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { apiGet, apiPost } from "@/lib/api";
import type { FacultyStudentDetail, PredictionResult } from "@/types";
import type { ExplanationPayload, Recommendation } from "@/types/advanced";

const MODEL_TYPES = [
  { value: "BASELINE", label: "Baseline ML" },
  { value: "TRANSFORMER", label: "Transformer" },
  { value: "HYBRID", label: "Hybrid" },
];

export default function FacultyStudentDetailPage() {
  const params = useParams<{ studentId: string }>();
  const studentId = params.studentId;
  const queryClient = useQueryClient();
  const [modelType, setModelType] = useState("BASELINE");
  const [interventionNote, setInterventionNote] = useState("");
  const [interventionType, setInterventionType] = useState("EXTRA_TUTORING");

  const detail = useQuery({
    queryKey: ["faculty-student-detail", studentId],
    queryFn: () => apiGet<FacultyStudentDetail>(`/faculty/students/${studentId}`),
  });

  const latestPredictionId = detail.data?.predictions[0]?.id;
  const explanation = useQuery({
    queryKey: ["faculty-explanation", latestPredictionId],
    queryFn: () => apiGet<ExplanationPayload>(`/predictions/${latestPredictionId}/explanation`),
    enabled: !!latestPredictionId,
  });

  const predict = useMutation({
    mutationFn: () =>
      apiPost<PredictionResult>(`/ml/predict/advanced`, {
        student_id: studentId,
        course_id: null,
        explain: true,
        recommend: true,
        model_type: modelType,
      }),
    onSuccess: () => {
      toast.success("Prediction generated");
      queryClient.invalidateQueries({ queryKey: ["faculty-student-detail", studentId] });
      queryClient.invalidateQueries({ queryKey: ["faculty-students"] });
    },
    onError: (error) => toast.error(error.message),
  });

  const intervention = useMutation({
    mutationFn: () =>
      apiPost("/interventions", {
        student_id: studentId,
        note: interventionNote,
        intervention_type: interventionType,
        prediction_id: latestPredictionId ?? null,
      }),
    onSuccess: () => {
      toast.success("Intervention recorded");
      setInterventionNote("");
    },
    onError: (error) => toast.error(error.message),
  });

  if (detail.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-72" />
        <Skeleton className="h-40" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  const data = detail.data;
  if (!data) {
    return <p className="p-8 text-center text-sm text-muted-foreground">Student not found or not in your courses.</p>;
  }

  const s = data.student;
  const currentAssessments = data.assessments.filter((a) => a.assessment_type !== "ENDTERM");
  const currentAvg =
    currentAssessments.length > 0
      ? Math.round(
          (currentAssessments.reduce((acc, a) => acc + (a.score / a.maximum_score) * 100, 0) /
            currentAssessments.length) *
            10,
        ) / 10
      : null;
  const attendancePct =
    data.attendance.length > 0
      ? Math.round(
          (data.attendance.reduce((acc, a) => acc + a.classes_attended, 0) /
            Math.max(1, data.attendance.reduce((acc, a) => acc + a.classes_conducted, 0))) *
            1000,
        ) / 10
      : null;
  const latestPrediction = data.predictions[0] ?? null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Button variant="ghost" size="sm" asChild className="-ml-2 mb-1">
            <Link href="/faculty/students">
              <ArrowLeft /> All students
            </Link>
          </Button>
          <h1 className="text-2xl font-semibold tracking-tight">{s.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {s.roll_number} · {s.department} · Year {s.year} · Semester {s.semester} · Section {s.section}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={modelType} onValueChange={setModelType}>
            <SelectTrigger className="w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MODEL_TYPES.map((m) => (
                <SelectItem key={m.value} value={m.value}>
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={() => predict.mutate()} disabled={predict.isPending}>
            <Sparkles />
            {predict.isPending ? "Generating…" : "Generate Prediction"}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardDescription>Current Performance</CardDescription>
            <CardTitle className="text-3xl">{currentAvg != null ? `${currentAvg}%` : "—"}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">Average across in-progress assessments</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Attendance</CardDescription>
            <CardTitle className="text-3xl">{attendancePct != null ? `${attendancePct}%` : "—"}</CardTitle>
          </CardHeader>
          <CardContent>
            <Progress value={attendancePct ?? 0} className="mt-1" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Predicted Score & Risk</CardDescription>
            <CardTitle className="text-3xl">{latestPrediction ? `${latestPrediction.predicted_score.toFixed(1)}%` : "—"}</CardTitle>
          </CardHeader>
          <CardContent>
            <RiskBadge level={latestPrediction?.risk_level} />
            {latestPrediction && (
              <p className="mt-2 text-xs text-muted-foreground">
                {latestPrediction.model_name} v{latestPrediction.model_version} ·{" "}
                {new Date(latestPrediction.prediction_date).toLocaleString()}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* AI explanation (§33) */}
      {latestPrediction && (
        <Card>
          <CardHeader>
            <CardTitle>AI Explanation</CardTitle>
            <CardDescription>
              SHAP/LIME factors behind the latest prediction
              {explanation.data?.prediction.model_type ? ` (${explanation.data.prediction.model_type})` : ""}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {explanation.isLoading ? (
              <Skeleton className="h-24" />
            ) : explanation.data ? (
              <div className="space-y-3">
                {explanation.data.summary && (
                  <p className="rounded-lg bg-muted/40 p-3 text-sm">{explanation.data.summary}</p>
                )}
                <FactorList factors={explanation.data.factors} max={6} />
                <p className="text-xs text-muted-foreground">{explanation.data.disclaimer}</p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No explanation available for this prediction.</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Recommendations (§33) */}
      <StudentRecommendations studentId={studentId} />

      {/* Faculty intervention (§34) */}
      <Card>
        <CardHeader>
          <CardTitle>Faculty Intervention</CardTitle>
          <CardDescription>
            Record a supportive action. AI predictions support faculty decision-making — they do not replace it.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1.5">
            <Label>Intervention type</Label>
            <Select value={interventionType} onValueChange={setInterventionType}>
              <SelectTrigger className="w-60">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["EXTRA_TUTORING", "COUNSELING", "STUDY_PLAN", "MENTORING", "PARENT_CONTACT", "OTHER"].map((t) => (
                  <SelectItem key={t} value={t}>
                    {t.replace("_", " ")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Note</Label>
            <Textarea
              rows={3}
              placeholder="e.g. Student shows declining performance in DBMS. Recommend additional academic support."
              value={interventionNote}
              onChange={(e) => setInterventionNote(e.target.value)}
            />
          </div>
          <Button onClick={() => intervention.mutate()} disabled={intervention.isPending || interventionNote.length < 5}>
            Record intervention
          </Button>
        </CardContent>
      </Card>

      <Tabs defaultValue="assessments">
        <TabsList>
          <TabsTrigger value="assessments">Assessments</TabsTrigger>
          <TabsTrigger value="attendance">Attendance</TabsTrigger>
          <TabsTrigger value="activity">Learning Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="assessments">
          <Card>
            <CardContent className="p-0">
              {data.assessments.length === 0 ? (
                <p className="p-8 text-center text-sm text-muted-foreground">No assessments recorded yet.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead className="text-right">Score</TableHead>
                      <TableHead className="text-right">Percentage</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.assessments.slice(0, 30).map((a) => (
                      <TableRow key={a.id}>
                        <TableCell>{new Date(a.assessment_date).toLocaleDateString()}</TableCell>
                        <TableCell>{a.assessment_type}</TableCell>
                        <TableCell className="text-right">
                          {a.score} / {a.maximum_score}
                        </TableCell>
                        <TableCell className="text-right">{Math.round((a.score / a.maximum_score) * 100)}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="attendance">
          <Card>
            <CardContent className="p-0">
              {data.attendance.length === 0 ? (
                <p className="p-8 text-center text-sm text-muted-foreground">No attendance recorded yet.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead className="text-right">Conducted</TableHead>
                      <TableHead className="text-right">Attended</TableHead>
                      <TableHead className="text-right">Percentage</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.attendance.slice(0, 30).map((a) => (
                      <TableRow key={a.id}>
                        <TableCell>{new Date(a.date).toLocaleDateString()}</TableCell>
                        <TableCell className="text-right">{a.classes_conducted}</TableCell>
                        <TableCell className="text-right">{a.classes_attended}</TableCell>
                        <TableCell className="text-right">{a.attendance_percentage}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity">
          <Card>
            <CardContent className="p-0">
              {data.activities.length === 0 ? (
                <p className="p-8 text-center text-sm text-muted-foreground">No learning activity recorded yet.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Date</TableHead>
                      <TableHead className="text-right">Session (min)</TableHead>
                      <TableHead className="text-right">Videos</TableHead>
                      <TableHead className="text-right">Quizzes</TableHead>
                      <TableHead className="text-right">Assignments</TableHead>
                      <TableHead className="text-right">Practice Qs</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.activities.slice(0, 30).map((a) => (
                      <TableRow key={a.id}>
                        <TableCell>{new Date(a.activity_date).toLocaleDateString()}</TableCell>
                        <TableCell className="text-right">{a.session_duration}</TableCell>
                        <TableCell className="text-right">
                          {a.videos_completed}/{a.videos_watched}
                        </TableCell>
                        <TableCell className="text-right">{a.quiz_attempts}</TableCell>
                        <TableCell className="text-right">{a.assignments_submitted}</TableCell>
                        <TableCell className="text-right">{a.practice_questions_attempted}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function StudentRecommendations({ studentId }: { studentId: string }) {
  const recommendations = useQuery({
    queryKey: ["faculty-student-recs", studentId],
    queryFn: () => apiGet<Recommendation[]>(`/students/${studentId}/recommendations`),
    retry: false,
  });

  return (
    <div>
      <h2 className="mb-3 text-lg font-semibold tracking-tight">Personalized recommendations</h2>
      {recommendations.isLoading ? (
        <Skeleton className="h-24" />
      ) : recommendations.isError ? (
        <p className="text-sm text-muted-foreground">
          Recommendations are visible to the student and to administrators.
        </p>
      ) : (
        <RecommendationList items={recommendations.data ?? []} />
      )}
    </div>
  );
}
