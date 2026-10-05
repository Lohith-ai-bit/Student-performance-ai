import { DashboardShell } from "@/components/dashboard/shell";

export default function FacultyLayout({ children }: { children: React.ReactNode }) {
  return <DashboardShell>{children}</DashboardShell>;
}
