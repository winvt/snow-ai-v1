import { cookies } from "next/headers";

import { AdminShell } from "../../components/admin-shell";
import { UsersScreen } from "../../components/users-screen";
import { requireAdminSession } from "../../lib/session";

export const dynamic = "force-dynamic";

export default function UsersPage() {
  requireAdminSession(cookies());
  return (
    <AdminShell activeTab="users">
      <UsersScreen />
    </AdminShell>
  );
}
