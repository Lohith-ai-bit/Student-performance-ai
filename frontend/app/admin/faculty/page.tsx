"use client";

import { useQuery } from "@tanstack/react-query";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { apiGet } from "@/lib/api";

interface FacultyRow {
  id: string;
  name: string;
  email: string;
  employee_id: string;
  department: string;
  designation: string;
  course_ids: string[];
}

export default function AdminFacultyPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-faculty"],
    queryFn: () => apiGet<FacultyRow[]>("/faculty"),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Faculty</h1>
        <p className="mt-1 text-sm text-muted-foreground">Teaching staff and their course assignments</p>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Employee ID</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Department</TableHead>
                  <TableHead>Designation</TableHead>
                  <TableHead className="text-right">Courses</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(data ?? []).map((f) => (
                  <TableRow key={f.id}>
                    <TableCell className="font-medium">{f.employee_id}</TableCell>
                    <TableCell>{f.name}</TableCell>
                    <TableCell className="text-muted-foreground">{f.email}</TableCell>
                    <TableCell className="max-w-48 truncate">{f.department}</TableCell>
                    <TableCell>{f.designation}</TableCell>
                    <TableCell className="text-right">{f.course_ids.length}</TableCell>
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
