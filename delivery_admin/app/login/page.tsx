import { cookies } from "next/headers";

import { LoginForm } from "../../components/login-form";
import { redirectIfAuthenticated } from "../../lib/session";

export const dynamic = "force-dynamic";

export default function LoginPage() {
  redirectIfAuthenticated(cookies());

  return (
    <main className="min-h-screen bg-muted/40 px-4 py-10">
      <section className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-8 lg:grid-cols-[1.1fr_440px]">
        <div className="hidden lg:block">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">Snow AI Delivery</p>
          <h1 className="mt-4 max-w-xl text-5xl font-bold tracking-tight text-foreground">Simple photo review for the delivery team.</h1>
          <p className="mt-4 max-w-lg text-lg text-muted-foreground">
            Sign in to browse visit photos, check GPS and timestamps, and manage which locations each LINE user can upload to.
          </p>
        </div>

        <div className="surface mx-auto w-full max-w-md p-6 sm:p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-primary">Snow AI Delivery</p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-foreground">Admin Login</h1>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Sign in to review photos, manage users, and keep location access under control.
          </p>
          <div className="mt-6">
            <LoginForm />
          </div>
        </div>
      </section>
    </main>
  );
}
