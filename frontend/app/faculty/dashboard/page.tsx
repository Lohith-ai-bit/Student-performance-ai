"use client";

import { useQuery } from "@tanstack/react-query";
import { CalendarCheck, TrendingDown, TrendingUp, Users } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { StatCard } from "@/components/stat-card";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { apiGet } from "@/lib/api";
import type { FacultyDashboard } from "@/types";

export default function FacultyDashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["faculty-dashboard"],
    queryFn: () => apiGet<FacultyDashboard>("/dashboards/faculty"),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-72" />
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-80" />
      </div>
    );
  }

  const totals = data?.totals;
  const riskData = (data?.risk_distribution ?? []).map((r) => ({ level: r.level, count: r.count }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Faculty Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Welcome, {data?.faculty_name} · overview of your assigned courses
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard title="Total Students" value={totals?.students ?? 0} icon={Users} />
        <StatCard
          title="Average Performance"
          value={totals?.avg_performance != null ? `${totals.avg_performance}%` : "—"}
          icon={TrendingUp}
        />
        <StatCard
          title="Average Attendance"
          value={totals?.avg_attendance != null ? `${totals.avg_attendance}%` : "—"}
          icon={CalendarCheck}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Critical Risk" value={totals?.critical_risk ?? 0} icon={TrendingDown} className="border-red-500 bg-red-50/40" />
        <StatCard title="High Risk" value={totals?.high_risk ?? 0} icon={TrendingDown} className="border-red-200" />
        <StatCard title="Medium Risk" value={totals?.medium_risk ?? 0} icon={TrendingDown} className="border-amber-200" />
        <StatCard title="Low Risk" value={totals?.low_risk ?? 0} icon={TrendingUp} className="border-emerald-200" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Performance Distribution</CardTitle>
            <CardDescription>Students per score band</CardDescription>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.performance_distribution ?? []}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="bucket" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip />
                <Bar dataKey="count" name="Students" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Risk Distribution</CardTitle>
            <CardDescription>Latest prediction per student</CardDescription>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={riskData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="level" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip />
                <Bar dataKey="count" name="Students" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Attendance Distribution</CardTitle>
            <CardDescription>Students per attendance band</CardDescription>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.attendance_distribution ?? []}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="bucket" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip />
                <Bar dataKey="count" name="Students" fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
