import { cookies } from "next/headers";

import { LoginForm } from "@/components/login-form";
import { redirectIfAuthenticated } from "@/lib/session";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  redirectIfAuthenticated(cookies());

  return (
    <main className="login-shell">
      <section className="login-card">
        <p className="eyebrow">Snow AI Delivery</p>
        <h1>Admin Login</h1>
        <p className="login-copy">
          Sign in to review visit photos, manage location access, and keep the delivery workflow moving.
        </p>
        <LoginForm />
      </section>
    </main>
  );
}
