"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, Search, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { RiskBadge } from "@/components/risk-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet, apiPost } from "@/lib/api";
import type { CourseInfo, FacultyStudentRow, PageMeta } from "@/types";
import type { BatchJob } from "@/types/advanced";

interface StudentsResponse {
  success: boolean;
  items: FacultyStudentRow[];
  meta: PageMeta;
}

export default function FacultyStudentsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [courseId, setCourseId] = useState("");
  const [riskLevel, setRiskLevel] = useState("");

  const courses = useQuery({
    queryKey: ["faculty-courses"],
    queryFn: () => apiGet<{ items: CourseInfo[] }>("/faculty/me/courses"),
  });
  const students = useQuery({
    queryKey: ["faculty-students", page, search, courseId, riskLevel],
    queryFn: () =>
      apiGet<StudentsResponse>("/faculty/students", {
        page,
        page_size: 15,
        search: search || undefined,
        course_id: courseId || undefined,
        risk_level: riskLevel || undefined,
      }),
  });
  const queryClient = useQueryClient();

  const batchPredict = useMutation({
    mutationFn: () =>
      apiPost<BatchJob>("/ml/batch-predictions", {
        scope: courseId ? "COURSE" : "DEPARTMENT",
        scope_id: courseId ?? "CSE",
        model_type: "BASELINE",
        run_inline: true,
      }),
    onSuccess: (job) => {
      toast.success(`Batch prediction ${job.status.toLowerCase()}: ${job.processed_items}/${job.total_items} students`);
      queryClient.invalidateQueries({ queryKey: ["faculty-students"] });
    },
    onError: (e) => toast.error(e.message),
  });

  const meta = students.data?.meta;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Students</h1>
          <p className="mt-1 text-sm text-muted-foreground">Enrolled students across your assigned courses</p>
        </div>
        <Button onClick={() => batchPredict.mutate()} disabled={batchPredict.isPending}>
          <Sparkles />
          {batchPredict.isPending
            ? "Predicting…"
            : `Batch predict ${courseId ? "course" : "department"}`}
        </Button>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-center gap-3 p-4">
          <div className="relative min-w-52 flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="Search by name or roll number…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <Select
            value={courseId}
            onValueChange={(v) => {
              setCourseId(v === "all" ? "" : v);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-52">
              <SelectValue placeholder="All courses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All courses</SelectItem>
              {(courses.data?.items ?? []).map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.course_code}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select
            value={riskLevel}
            onValueChange={(v) => {
              setRiskLevel(v === "all" ? "" : v);
              setPage(1);
            }}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Any risk" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Any risk</SelectItem>
              <SelectItem value="LOW">Low</SelectItem>
              <SelectItem value="MEDIUM">Medium</SelectItem>
              <SelectItem value="HIGH">High</SelectItem>
              <SelectItem value="CRITICAL">Critical</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          {students.isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : (students.data?.items ?? []).length === 0 ? (
            <p className="p-10 text-center text-sm text-muted-foreground">No students match the current filters.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Student</TableHead>
                  <TableHead>Roll Number</TableHead>
                  <TableHead>Department</TableHead>
                  <TableHead className="text-right">Performance</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead className="text-right">Predicted</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {(students.data?.items ?? []).map((s) => (
                  <TableRow key={s.student_id}>
                    <TableCell>
                      <Link href={`/faculty/students/${s.student_id}`} className="font-medium hover:text-primary hover:underline">
                        {s.name}
                      </Link>
                      <p className="text-xs text-muted-foreground">{s.section}</p>
                    </TableCell>
                    <TableCell>{s.roll_number}</TableCell>
                    <TableCell className="max-w-40 truncate">{s.department}</TableCell>
                    <TableCell className="text-right">
                      {s.predicted_score != null ? `${s.predicted_score.toFixed(1)}%` : "—"}
                    </TableCell>
                    <TableCell>
                      <RiskBadge level={s.risk_level} />
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {s.predicted_score != null ? "Latest" : "—"}
                    </TableCell>
                    <TableCell>
                      <Link href={`/faculty/students/${s.student_id}`} aria-label="Open student">
                        <ChevronRight className="h-4 w-4" />
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {meta && meta.total_pages > 1 && (
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>
            Page {meta.page} of {meta.total_pages} · {meta.total} students
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= meta.total_pages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
