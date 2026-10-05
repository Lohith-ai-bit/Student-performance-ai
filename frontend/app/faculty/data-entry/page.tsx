"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { ClipboardList } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiGet, apiPost } from "@/lib/api";
import type { CourseInfo, FacultyStudentRow } from "@/types";

function useStudentOptions() {
  return useQuery({
    queryKey: ["faculty-students-options"],
    queryFn: () => apiGet<{ items: FacultyStudentRow[] }>("/faculty/students", { page: 1, page_size: 100 }),
  });
}

function useCourseOptions() {
  return useQuery({
    queryKey: ["faculty-courses"],
    queryFn: () => apiGet<{ items: CourseInfo[] }>("/faculty/me/courses"),
  });
}

function StudentSelect({
  value,
  onChange,
  students,
}: {
  value: string;
  onChange: (v: string) => void;
  students: FacultyStudentRow[];
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger>
        <SelectValue placeholder="Select student" />
      </SelectTrigger>
      <SelectContent>
        {students.map((s) => (
          <SelectItem key={s.student_id} value={s.student_id}>
            {s.roll_number} — {s.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function CourseSelect({
  value,
  onChange,
  courses,
}: {
  value: string;
  onChange: (v: string) => void;
  courses: CourseInfo[];
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger>
        <SelectValue placeholder="Select course" />
      </SelectTrigger>
      <SelectContent>
        {courses.map((c) => (
          <SelectItem key={c.id} value={c.id}>
            {c.course_code} — {c.course_name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

const assessmentSchema = z.object({
  student_id: z.string().min(1, "Select a student"),
  course_id: z.string().min(1, "Select a course"),
  assessment_type: z.string().min(1, "Select a type"),
  score: z.coerce.number().min(0, "Score must be >= 0"),
  maximum_score: z.coerce.number().positive("Maximum score must be > 0"),
  assessment_date: z.string().min(1, "Date is required"),
});
const attendanceSchema = z.object({
  student_id: z.string().min(1, "Select a student"),
  course_id: z.string().min(1, "Select a course"),
  classes_conducted: z.coerce.number().int().min(0),
  classes_attended: z.coerce.number().int().min(0),
  date: z.string().min(1, "Date is required"),
});
const activitySchema = z.object({
  student_id: z.string().min(1, "Select a student"),
  course_id: z.string().min(1, "Select a course"),
  activity_date: z.string().min(1, "Date is required"),
  session_duration: z.coerce.number().min(0),
  videos_watched: z.coerce.number().min(0),
  videos_completed: z.coerce.number().min(0),
  quiz_attempts: z.coerce.number().min(0),
  assignments_submitted: z.coerce.number().min(0),
  late_submissions: z.coerce.number().min(0),
  practice_questions_attempted: z.coerce.number().min(0),
  login_count: z.coerce.number().min(0),
});

type AssessmentForm = z.infer<typeof assessmentSchema>;
type AttendanceForm = z.infer<typeof attendanceSchema>;
type ActivityForm = z.infer<typeof activitySchema>;

export default function FacultyDataEntryPage() {
  const students = useStudentOptions();
  const courses = useCourseOptions();
  const studentList = students.data?.items ?? [];
  const courseList = courses.data?.items ?? [];

  const assessmentForm = useForm<AssessmentForm>({ resolver: zodResolver(assessmentSchema) });
  const attendanceForm = useForm<AttendanceForm>({ resolver: zodResolver(attendanceSchema) });
  const activityForm = useForm<ActivityForm>({ resolver: zodResolver(activitySchema) });

  const onAssessment = assessmentForm.handleSubmit(async (values) => {
    try {
      await apiPost("/faculty/assessments", values);
      toast.success("Assessment recorded");
      assessmentForm.reset();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to record assessment");
    }
  });
  const onAttendance = attendanceForm.handleSubmit(async (values) => {
    try {
      await apiPost("/faculty/attendance", values);
      toast.success("Attendance recorded");
      attendanceForm.reset();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to record attendance");
    }
  });
  const onActivity = activityForm.handleSubmit(async (values) => {
    try {
      await apiPost("/faculty/activities", values);
      toast.success("Learning activity recorded");
      activityForm.reset();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to record activity");
    }
  });

  const field = "space-y-1.5";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Data Entry</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Record assessments, attendance and learning activity for your enrolled students
        </p>
      </div>

      <Card>
        <CardContent className="pt-6">
          <Tabs defaultValue="assessment">
            <TabsList>
              <TabsTrigger value="assessment">Assessment</TabsTrigger>
              <TabsTrigger value="attendance">Attendance</TabsTrigger>
              <TabsTrigger value="activity">Learning Activity</TabsTrigger>
            </TabsList>

            {/* Assessment */}
            <TabsContent value="assessment">
              <form onSubmit={onAssessment} className="grid gap-4 sm:grid-cols-2" noValidate>
                <div className={field}>
                  <Label>Student</Label>
                  <StudentSelect
                    value={assessmentForm.watch("student_id") ?? ""}
                    onChange={(v) => assessmentForm.setValue("student_id", v)}
                    students={studentList}
                  />
                  {assessmentForm.formState.errors.student_id && (
                    <p className="text-xs text-destructive">{assessmentForm.formState.errors.student_id.message}</p>
                  )}
                </div>
                <div className={field}>
                  <Label>Course</Label>
                  <CourseSelect
                    value={assessmentForm.watch("course_id") ?? ""}
                    onChange={(v) => assessmentForm.setValue("course_id", v)}
                    courses={courseList}
                  />
                  {assessmentForm.formState.errors.course_id && (
                    <p className="text-xs text-destructive">{assessmentForm.formState.errors.course_id.message}</p>
                  )}
                </div>
                <div className={field}>
                  <Label>Assessment Type</Label>
                  <Select onValueChange={(v) => assessmentForm.setValue("assessment_type", v)}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      {["QUIZ", "ASSIGNMENT", "MIDTERM", "ENDTERM", "LAB", "PROJECT", "OTHER"].map((t) => (
                        <SelectItem key={t} value={t}>
                          {t}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className={field}>
                  <Label>Date</Label>
                  <Input type="date" {...assessmentForm.register("assessment_date")} />
                </div>
                <div className={field}>
                  <Label>Score</Label>
                  <Input type="number" step="0.5" {...assessmentForm.register("score")} />
                  {assessmentForm.formState.errors.score && (
                    <p className="text-xs text-destructive">{assessmentForm.formState.errors.score.message}</p>
                  )}
                </div>
                <div className={field}>
                  <Label>Maximum Score</Label>
                  <Input type="number" step="0.5" {...assessmentForm.register("maximum_score")} />
                  {assessmentForm.formState.errors.maximum_score && (
                    <p className="text-xs text-destructive">{assessmentForm.formState.errors.maximum_score.message}</p>
                  )}
                </div>
                <div className="sm:col-span-2">
                  <Button type="submit" disabled={assessmentForm.formState.isSubmitting}>
                    <ClipboardList /> Save Assessment
                  </Button>
                </div>
              </form>
            </TabsContent>

            {/* Attendance */}
            <TabsContent value="attendance">
              <form onSubmit={onAttendance} className="grid gap-4 sm:grid-cols-2" noValidate>
                <div className={field}>
                  <Label>Student</Label>
                  <StudentSelect
                    value={attendanceForm.watch("student_id") ?? ""}
                    onChange={(v) => attendanceForm.setValue("student_id", v)}
                    students={studentList}
                  />
                </div>
                <div className={field}>
                  <Label>Course</Label>
                  <CourseSelect
                    value={attendanceForm.watch("course_id") ?? ""}
                    onChange={(v) => attendanceForm.setValue("course_id", v)}
                    courses={courseList}
                  />
                </div>
                <div className={field}>
                  <Label>Classes Conducted</Label>
                  <Input type="number" min={0} {...attendanceForm.register("classes_conducted")} />
                </div>
                <div className={field}>
                  <Label>Classes Attended</Label>
                  <Input type="number" min={0} {...attendanceForm.register("classes_attended")} />
                  <p className="text-xs text-muted-foreground">
                    Percentage is calculated automatically (attended / conducted × 100)
                  </p>
                </div>
                <div className={field}>
                  <Label>Date</Label>
                  <Input type="date" {...attendanceForm.register("date")} />
                </div>
                <div className="flex items-end">
                  <Button type="submit" disabled={attendanceForm.formState.isSubmitting}>
                    <ClipboardList /> Save Attendance
                  </Button>
                </div>
              </form>
            </TabsContent>

            {/* Learning activity */}
            <TabsContent value="activity">
              <form onSubmit={onActivity} className="grid gap-4 sm:grid-cols-3" noValidate>
                <div className={field}>
                  <Label>Student</Label>
                  <StudentSelect
                    value={activityForm.watch("student_id") ?? ""}
                    onChange={(v) => activityForm.setValue("student_id", v)}
                    students={studentList}
                  />
                </div>
                <div className={field}>
                  <Label>Course</Label>
                  <CourseSelect
                    value={activityForm.watch("course_id") ?? ""}
                    onChange={(v) => activityForm.setValue("course_id", v)}
                    courses={courseList}
                  />
                </div>
                <div className={field}>
                  <Label>Date</Label>
                  <Input type="date" {...activityForm.register("activity_date")} />
                </div>
                <div className={field}>
                  <Label>Session Duration (min)</Label>
                  <Input type="number" min={0} {...activityForm.register("session_duration")} />
                </div>
                <div className={field}>
                  <Label>Videos Watched</Label>
                  <Input type="number" min={0} {...activityForm.register("videos_watched")} />
                </div>
                <div className={field}>
                  <Label>Videos Completed</Label>
                  <Input type="number" min={0} {...activityForm.register("videos_completed")} />
                </div>
                <div className={field}>
                  <Label>Quiz Attempts</Label>
                  <Input type="number" min={0} {...activityForm.register("quiz_attempts")} />
                </div>
                <div className={field}>
                  <Label>Assignments Submitted</Label>
                  <Input type="number" min={0} {...activityForm.register("assignments_submitted")} />
                </div>
                <div className={field}>
                  <Label>Late Submissions</Label>
                  <Input type="number" min={0} {...activityForm.register("late_submissions")} />
                </div>
                <div className={field}>
                  <Label>Practice Questions</Label>
                  <Input type="number" min={0} {...activityForm.register("practice_questions_attempted")} />
                </div>
                <div className="flex items-end sm:col-span-3">
                  <Button type="submit" disabled={activityForm.formState.isSubmitting}>
                    <ClipboardList /> Save Activity
                  </Button>
                </div>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
