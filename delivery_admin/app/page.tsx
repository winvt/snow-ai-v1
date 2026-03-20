import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { isAdminAuthenticated } from "@/lib/session";

export const dynamic = "force-dynamic";

export default function HomePage() {
  const cookieStore = cookies();
  redirect(isAdminAuthenticated(cookieStore) ? "/reports" : "/login");
}
