"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiDelete, apiGet, apiPost } from "@/lib/api";

interface Department {
  id: string;
  name: string;
  code: string;
}

interface Course {
  id: string;
  course_code: string;
  course_name: string;
  credits: number;
  department_id: string | null;
  semester: number;
}

export default function AdminDepartmentsPage() {
  const queryClient = useQueryClient();
  const departments = useQuery({ queryKey: ["departments"], queryFn: () => apiGet<Department[]>("/departments") });
  const courses = useQuery({ queryKey: ["courses"], queryFn: () => apiGet<Course[]>("/courses") });

  const [deptName, setDeptName] = useState("");
  const [deptCode, setDeptCode] = useState("");
  const [courseCode, setCourseCode] = useState("");
  const [courseName, setCourseName] = useState("");
  const [courseCredits, setCourseCredits] = useState("3");
  const [courseSemester, setCourseSemester] = useState("3");

  const createDepartment = useMutation({
    mutationFn: () => apiPost("/departments", { name: deptName, code: deptCode }),
    onSuccess: () => {
      toast.success("Department created");
      setDeptName("");
      setDeptCode("");
      queryClient.invalidateQueries({ queryKey: ["departments"] });
    },
    onError: (e) => toast.error(e.message),
  });

  const createCourse = useMutation({
    mutationFn: () =>
      apiPost("/courses", {
        course_code: courseCode,
        course_name: courseName,
        credits: Number(courseCredits),
        semester: Number(courseSemester),
        department_id: departments.data?.[0]?.id ?? null,
      }),
    onSuccess: () => {
      toast.success("Course created");
      setCourseCode("");
      setCourseName("");
      queryClient.invalidateQueries({ queryKey: ["courses"] });
    },
    onError: (e) => toast.error(e.message),
  });

  const deleteDepartment = useMutation({
    mutationFn: (id: string) => apiDelete(`/departments/${id}`),
    onSuccess: () => {
      toast.success("Department deleted");
      queryClient.invalidateQueries({ queryKey: ["departments"] });
    },
    onError: (e) => toast.error(e.message),
  });

  const deleteCourse = useMutation({
    mutationFn: (id: string) => apiDelete(`/courses/${id}`),
    onSuccess: () => {
      toast.success("Course deleted");
      queryClient.invalidateQueries({ queryKey: ["courses"] });
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Departments & Courses</h1>
        <p className="mt-1 text-sm text-muted-foreground">Manage the academic catalogue</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Create Department</CardTitle>
            <CardDescription>Departments group courses and analytics</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="dept-name">Name</Label>
              <Input id="dept-name" value={deptName} onChange={(e) => setDeptName(e.target.value)} placeholder="e.g. Biotechnology" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="dept-code">Code</Label>
              <Input id="dept-code" value={deptCode} onChange={(e) => setDeptCode(e.target.value)} placeholder="e.g. BT" />
            </div>
            <Button onClick={() => createDepartment.mutate()} disabled={!deptName || !deptCode || createDepartment.isPending}>
              <Plus /> Create
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Create Course</CardTitle>
            <CardDescription>Courses belong to the first department by default</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="course-code">Code</Label>
                <Input id="course-code" value={courseCode} onChange={(e) => setCourseCode(e.target.value)} placeholder="e.g. BT401" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="course-credits">Credits</Label>
                <Input id="course-credits" type="number" min={1} max={10} value={courseCredits} onChange={(e) => setCourseCredits(e.target.value)} />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="course-name">Name</Label>
              <Input id="course-name" value={courseName} onChange={(e) => setCourseName(e.target.value)} placeholder="e.g. Cell Biology" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="course-sem">Semester</Label>
              <Input id="course-sem" type="number" min={1} max={12} value={courseSemester} onChange={(e) => setCourseSemester(e.target.value)} />
            </div>
            <Button onClick={() => createCourse.mutate()} disabled={!courseCode || !courseName || createCourse.isPending}>
              <Plus /> Create
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Departments ({departments.data?.length ?? 0})</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Code</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {(departments.data ?? []).map((d) => (
                  <TableRow key={d.id}>
                    <TableCell className="font-medium">{d.code}</TableCell>
                    <TableCell className="max-w-56 truncate">{d.name}</TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" className="text-destructive" onClick={() => deleteDepartment.mutate(d.id)}>
                        Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Courses ({courses.data?.length ?? 0})</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="max-h-96 overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Code</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead className="text-right">Sem</TableHead>
                    <TableHead className="w-10" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(courses.data ?? []).map((c) => (
                    <TableRow key={c.id}>
                      <TableCell className="font-medium">{c.course_code}</TableCell>
                      <TableCell className="max-w-48 truncate">{c.course_name}</TableCell>
                      <TableCell className="text-right">{c.semester}</TableCell>
                      <TableCell>
                        <Button variant="ghost" size="sm" className="text-destructive" onClick={() => deleteCourse.mutate(c.id)}>
                          Delete
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
