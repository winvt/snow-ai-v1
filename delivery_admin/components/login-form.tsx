"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export function LoginForm() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({ password }),
      });
      const payload = (await response.json().catch(() => ({}))) as { detail?: string };
      if (!response.ok) {
        throw new Error(payload.detail || "Could not sign in.");
      }
      router.push("/reports");
      router.refresh();
    } catch (caughtError) {
      const message = caughtError instanceof Error ? caughtError.message : "Could not sign in.";
      setError(message);
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="login-form" onSubmit={handleSubmit}>
      <label className="field">
        <span>Password</span>
        <input
          autoFocus
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Enter admin password"
        />
      </label>
      {error ? <p className="form-error">{error}</p> : null}
      <button className="primary-button wide-button" type="submit" disabled={pending}>
        {pending ? "Signing in..." : "Enter Admin"}
      </button>
    </form>
  );
}
