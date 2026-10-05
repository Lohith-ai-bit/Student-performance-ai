"use client";

import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet } from "@/lib/api";
import type { Assessment, StudentDashboard } from "@/types";

export default function StudentPerformancePage() {
  const dashboard = useQuery({
    queryKey: ["student-dashboard"],
    queryFn: () => apiGet<StudentDashboard>("/students/me/dashboard"),
  });
  const assessments = useQuery({
    queryKey: ["student-assessments"],
    queryFn: () => apiGet<Assessment[]>("/students/me/assessments"),
  });

  const isLoading = dashboard.isLoading || assessments.isLoading;
  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-72" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  const performance = dashboard.data?.performance ?? [];
  const chartData = performance.map((p) => ({
    course: p.course_code,
    current: p.current_average ?? 0,
    final: p.final_average ?? 0,
  }));
  const courseName = (id: string) => performance.find((p) => p.course_id === id)?.course_code ?? id.slice(0, 8);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">My Performance</h1>
        <p className="mt-1 text-sm text-muted-foreground">Subject-wise marks, assessment history and trends</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Subject Comparison</CardTitle>
          <CardDescription>Current (in-progress) vs completed average, percentage</CardDescription>
        </CardHeader>
        <CardContent>
          {chartData.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">No assessment data available yet.</p>
          ) : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="course" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis domain={[0, 100]} fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip />
                  <Bar dataKey="current" name="Current average" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="final" name="Completed average" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Assessment Marks</CardTitle>
          <CardDescription>Latest records across all courses</CardDescription>
        </CardHeader>
        <CardContent>
          {(assessments.data ?? []).length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No assessments recorded yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Course</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                  <TableHead className="text-right">Percentage</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(assessments.data ?? []).slice(0, 50).map((a) => (
                  <TableRow key={a.id}>
                    <TableCell>{new Date(a.assessment_date).toLocaleDateString()}</TableCell>
                    <TableCell className="font-medium">{courseName(a.course_id)}</TableCell>
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
    </div>
  );
}
