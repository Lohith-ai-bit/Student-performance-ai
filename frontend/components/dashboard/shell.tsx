"use client";

import { GraduationCap, LayoutDashboard, LogOut, Users } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth-provider";
import { NotificationsBell } from "@/components/notifications-bell";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Role } from "@/types";

const NAV: Record<Role, { href: string; label: string }[]> = {
  STUDENT: [
    { href: "/student/dashboard", label: "Dashboard" },
    { href: "/student/performance", label: "Performance" },
    { href: "/student/attendance", label: "Attendance" },
    { href: "/student/prediction", label: "Prediction" },
    { href: "/student/prediction/history", label: "Prediction History" },
    { href: "/student/learning", label: "My Learning" },
    { href: "/student/resources", label: "Resources" },
  ],
  FACULTY: [
    { href: "/faculty/dashboard", label: "Dashboard" },
    { href: "/faculty/students", label: "Students" },
    { href: "/faculty/data-entry", label: "Data Entry" },
    { href: "/faculty/import", label: "CSV Import" },
  ],
  ADMIN: [
    { href: "/admin/dashboard", label: "Dashboard" },
    { href: "/admin/students", label: "Students" },
    { href: "/admin/faculty", label: "Faculty" },
    { href: "/admin/departments", label: "Departments & Courses" },
    { href: "/admin/models", label: "Model Registry" },
    { href: "/admin/experiments", label: "Experiments" },
    { href: "/admin/monitoring", label: "Monitoring" },
  ],
};

const ROLE_LABEL: Record<Role, string> = {
  STUDENT: "Student Portal",
  FACULTY: "Faculty Portal",
  ADMIN: "Admin Console",
};

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const { user, logout, loading } = useAuth();
  const pathname = usePathname();

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    );
  }

  const nav = NAV[user.role];

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col border-r bg-card/60 backdrop-blur md:flex">
        <div className="flex items-center gap-2 px-5 py-5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <GraduationCap className="h-4.5 w-4.5" />
          </span>
          <div className="leading-tight">
            <p className="text-sm font-semibold">EduPredict</p>
            <p className="text-xs text-muted-foreground">{ROLE_LABEL[user.role]}</p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-2">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "block rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                pathname === item.href || pathname.startsWith(item.href + "/")
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground",
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="border-t p-4">
          <div className="mb-2 flex items-start justify-between gap-2 px-1">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{user.name}</p>
              <p className="truncate text-xs text-muted-foreground">{user.email}</p>
            </div>
            <NotificationsBell />
          </div>
          <Button variant="outline" size="sm" className="w-full" onClick={logout}>
            <LogOut /> Log out
          </Button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar */}
        <header className="flex items-center justify-between border-b bg-card/60 px-4 py-3 backdrop-blur md:hidden">
          <Link href={nav[0].href} className="flex items-center gap-2 font-semibold">
            <GraduationCap className="h-5 w-5 text-primary" /> EduPredict
          </Link>
          <div className="flex items-center gap-1">
            <NotificationsBell />
            <Button variant="ghost" size="sm" onClick={logout}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </header>
        <nav className="flex gap-1 overflow-x-auto border-b bg-card/60 px-3 py-2 backdrop-blur md:hidden">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium",
                pathname === item.href ? "bg-accent text-accent-foreground" : "text-muted-foreground",
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 md:px-8">{children}</main>
      </div>
    </div>
  );
}
