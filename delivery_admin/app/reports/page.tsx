import { cookies } from "next/headers";

import { AdminShell } from "@/components/admin-shell";
import { ReportsScreen } from "@/components/reports-screen";
import { requireAdminSession } from "@/lib/session";

export const dynamic = "force-dynamic";

export default function ReportsPage() {
  requireAdminSession(cookies());
  return (
    <AdminShell activeTab="reports">
      <ReportsScreen />
    </AdminShell>
  );
}
