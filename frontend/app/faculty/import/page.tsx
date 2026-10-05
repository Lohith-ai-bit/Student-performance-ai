"use client";

import { useMutation } from "@tanstack/react-query";
import { FileUp, ShieldAlert } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiUpload } from "@/lib/api";
import type { ImportReport } from "@/types";

interface PreviewResponse {
  success: boolean;
  report: ImportReport;
  preview_rows: Record<string, unknown>[];
}

const TEMPLATE = `student_id,course,attendance,quiz_score,assignment_score,midterm_score,date
S001,CS301,87,82,90,76,2026-09-20
S002,CS301,64,61,68,55,2026-09-20`;

export default function FacultyImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const previewMutation = useMutation({
    mutationFn: (f: File) => apiUpload<PreviewResponse>("/faculty/imports/csv/preview", f),
    onSuccess: setPreview,
    onError: (e) => toast.error(e.message),
  });

  const confirmMutation = useMutation({
    mutationFn: (f: File) => apiUpload<{ report: ImportReport }>("/faculty/imports/csv/confirm", f),
    onSuccess: (data) => {
      setPreview(null);
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      toast.success(data.report.message);
    },
    onError: (e) => toast.error(e.message),
  });

  function downloadTemplate() {
    const blob = new Blob([TEMPLATE], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "import-template.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">CSV Import</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Bulk-import academic records. Every invalid row is reported — nothing is silently discarded.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>1 · Upload & Preview</CardTitle>
          <CardDescription>
            Required columns: student_id (roll number), course (course code). Optional: attendance,
            classes_conducted/classes_attended, quiz_score, assignment_score, midterm_score, endterm_score, date
            (YYYY-MM-DD). Scores are 0–100.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <input
              ref={inputRef}
              type="file"
              accept=".csv"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setPreview(null);
              }}
              className="block w-full max-w-sm rounded-lg border border-input bg-card p-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-secondary file:px-3 file:py-1.5 file:text-sm"
            />
            <Button onClick={() => file && previewMutation.mutate(file)} disabled={!file || previewMutation.isPending}>
              <FileUp /> {previewMutation.isPending ? "Validating…" : "Validate & Preview"}
            </Button>
            <Button variant="link" onClick={downloadTemplate}>
              Download template
            </Button>
          </div>

          {preview && (
            <div className="space-y-4 rounded-lg border bg-muted/30 p-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-lg bg-card p-3 text-center shadow-sm">
                  <p className="text-xs text-muted-foreground">Total rows</p>
                  <p className="text-xl font-semibold">{preview.report.total_rows}</p>
                </div>
                <div className="rounded-lg bg-card p-3 text-center shadow-sm">
                  <p className="text-xs text-muted-foreground">Valid</p>
                  <p className="text-xl font-semibold text-emerald-600">{preview.report.valid_rows}</p>
                </div>
                <div className="rounded-lg bg-card p-3 text-center shadow-sm">
                  <p className="text-xs text-muted-foreground">Invalid</p>
                  <p className="text-xl font-semibold text-red-600">{preview.report.invalid_rows}</p>
                </div>
                <div className="rounded-lg bg-card p-3 text-center shadow-sm">
                  <p className="text-xs text-muted-foreground">To insert</p>
                  <p className="text-xl font-semibold">{preview.report.valid_rows}</p>
                </div>
              </div>

              {preview.report.errors.length > 0 && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3">
                  <p className="mb-2 flex items-center gap-2 text-sm font-medium text-red-700">
                    <ShieldAlert className="h-4 w-4" /> Problems found ({preview.report.errors.length})
                  </p>
                  <ul className="max-h-40 space-y-1 overflow-y-auto text-xs text-red-600">
                    {preview.report.errors.map((err, i) => (
                      <li key={i}>
                        Row {err.row}, {err.field}: {err.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {preview.preview_rows.length > 0 && (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Row</TableHead>
                      <TableHead>Student</TableHead>
                      <TableHead>Course</TableHead>
                      <TableHead className="text-right">Attendance</TableHead>
                      <TableHead className="text-right">Records to create</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {preview.preview_rows.map((row) => {
                      const r = row as {
                        row_number: number;
                        student_id: string;
                        course: string;
                        attendance: number | null;
                        scores: Record<string, number>;
                      };
                      return (
                        <TableRow key={r.row_number}>
                          <TableCell>{r.row_number}</TableCell>
                          <TableCell>{r.student_id}</TableCell>
                          <TableCell>{r.course}</TableCell>
                          <TableCell className="text-right">{r.attendance ?? "—"}</TableCell>
                          <TableCell className="text-right">
                            {Object.keys(r.scores).length + (r.attendance != null ? 1 : 0)}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}

              <div className="flex items-center gap-3">
                <Button
                  onClick={() => file && confirmMutation.mutate(file)}
                  disabled={confirmMutation.isPending || preview.report.valid_rows === 0}
                >
                  {confirmMutation.isPending
                    ? "Importing…"
                    : `2 · Confirm Import (${preview.report.valid_rows} valid rows)`}
                </Button>
                <Button variant="ghost" onClick={() => setPreview(null)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
