"use client";

import Link from "next/link";
import { ReactNode, useEffect, useState } from "react";

import { LogoutButton } from "./logout-button";
import type { AdminSystemStatus } from "../lib/types";

type AdminShellProps = {
  activeTab: "reports" | "users";
  children: ReactNode;
};

const fallbackSystemStatus: AdminSystemStatus = {
  database: {
    label: "Checking...",
    detail: "Verifying report storage.",
    persistent: true,
  },
  photoStorage: {
    label: "Checking...",
    detail: "Verifying photo storage.",
  },
};

export function AdminShell({ activeTab, children }: AdminShellProps) {
  const [systemStatus, setSystemStatus] = useState<AdminSystemStatus>(fallbackSystemStatus);
  const [systemError, setSystemError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadSystemStatus() {
      try {
        const response = await fetch("/api/admin/system", { cache: "no-store" });
        const payload = (await response.json().catch(() => ({}))) as AdminSystemStatus & { detail?: string };
        if (!response.ok) {
          throw new Error(payload.detail || "Could not load system status.");
        }
        if (active) {
          setSystemStatus(payload);
          setSystemError("");
        }
      } catch (caughtError) {
        if (active) {
          setSystemError(caughtError instanceof Error ? caughtError.message : "Could not load system status.");
        }
      }
    }

    void loadSystemStatus();
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="admin-app">
      <header className="admin-hero">
        <div className="hero-copy">
          <p className="eyebrow">Snow AI Delivery</p>
          <h1>Admin</h1>
          <p className="hero-subtitle">Reports, photos, and location access.</p>
        </div>
        <div className="hero-actions">
          <nav className="admin-nav" aria-label="Admin sections">
            <Link className={`admin-nav-link ${activeTab === "reports" ? "is-active" : ""}`} href="/reports">
              Reports
            </Link>
            <Link className={`admin-nav-link ${activeTab === "users" ? "is-active" : ""}`} href="/users">
              Users
            </Link>
          </nav>
          <LogoutButton />
        </div>
      </header>

      <section className={`system-strip ${systemStatus.database.persistent === false ? "is-warning" : ""}`}>
        <article className="system-card">
          <p className="toolbar-label">Report database</p>
          <strong>{systemStatus.database.label}</strong>
          <p>{systemStatus.database.detail}</p>
          {systemStatus.database.warning ? <p className="system-warning">{systemStatus.database.warning}</p> : null}
        </article>
        <article className="system-card">
          <p className="toolbar-label">Photo storage</p>
          <strong>{systemStatus.photoStorage.label}</strong>
          <p>{systemStatus.photoStorage.detail}</p>
        </article>
      </section>

      {systemError ? <p className="inline-error">{systemError}</p> : null}

      {children}
    </main>
  );
}
