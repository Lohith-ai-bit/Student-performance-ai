"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";

import { StatCard } from "@/components/stat-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Attendance, StudentDashboard } from "@/types";

export default function StudentAttendancePage() {
  const dashboard = useQuery({
    queryKey: ["student-dashboard"],
    queryFn: () => apiGet<StudentDashboard>("/students/me/dashboard"),
  });
  const records = useQuery({
    queryKey: ["student-attendance"],
    queryFn: () => apiGet<Attendance[]>("/students/me/attendance"),
  });

  const isLoading = dashboard.isLoading || records.isLoading;
  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-28" />
        <Skeleton className="h-72" />
      </div>
    );
  }

  const rows = (dashboard.data?.attendance ?? []).filter((a) => a.percentage !== null);
  const overall = dashboard.data?.summary.attendance_percentage;
  const lowSubjects = rows.filter((r) => r.percentage !== null && r.percentage < 75);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">My Attendance</h1>
        <p className="mt-1 text-sm text-muted-foreground">Overall attendance, subject breakdown and records</p>
      </div>

      <StatCard
        title="Overall Attendance"
        value={overall != null ? `${overall}%` : "—"}
        hint={overall != null && overall < 75 ? "Below the common 75% requirement" : "Keep it up!"}
        className={cn(overall != null && overall < 75 && "border-destructive/30")}
      />

      {lowSubjects.length > 0 && (
        <Card className="border-amber-200 bg-amber-50/60">
          <CardContent className="flex items-start gap-3 p-4">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-600" />
            <div>
              <p className="text-sm font-medium text-amber-800">Low attendance alert</p>
              <p className="text-sm text-amber-700">
                Below 75%: {lowSubjects.map((s) => `${s.course_code} (${s.percentage}%)`).join(", ")}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Subject Attendance</CardTitle>
          <CardDescription>Percentage of classes attended per course</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {rows.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No attendance recorded yet.</p>
          ) : (
            rows.map((row) => (
              <div key={row.course_id}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="font-medium">{row.course_code}</span>
                  <span className={cn(row.percentage !== null && row.percentage < 75 && "text-destructive")}>
                    {row.percentage}% ({row.classes_attended}/{row.classes_conducted})
                  </span>
                </div>
                <Progress
                  value={row.percentage ?? 0}
                  indicatorClassName={row.percentage !== null && row.percentage < 75 ? "bg-destructive" : undefined}
                />
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Attendance Records</CardTitle>
          <CardDescription>Monthly records as reported by faculty</CardDescription>
        </CardHeader>
        <CardContent>
          {(records.data ?? []).length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No attendance records yet.</p>
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
                {(records.data ?? []).slice(0, 30).map((row) => (
                  <TableRow key={row.id}>
                    <TableCell>{new Date(row.date).toLocaleDateString()}</TableCell>
                    <TableCell className="text-right">{row.classes_conducted}</TableCell>
                    <TableCell className="text-right">{row.classes_attended}</TableCell>
                    <TableCell
                      className={cn("text-right", row.attendance_percentage < 75 && "font-medium text-destructive")}
                    >
                      {row.attendance_percentage}%
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
