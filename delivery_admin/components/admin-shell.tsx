"use client";

import Link from "next/link";
import { Camera, Database, LayoutList, Menu, Users, X } from "lucide-react";
import { ReactNode, useEffect, useState } from "react";

import { LogoutButton } from "./logout-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
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

const navItems = [
  { href: "/reports", label: "Reports", icon: Camera },
  { href: "/users", label: "Users", icon: Users },
] as const;

export function AdminShell({ activeTab, children }: AdminShellProps) {
  const [systemStatus, setSystemStatus] = useState<AdminSystemStatus>(fallbackSystemStatus);
  const [systemError, setSystemError] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [systemOpen, setSystemOpen] = useState(false);

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

  const sidebarContent = (
    <>
      <div className="border-b px-4 py-5">
        <p className="text-xl font-bold tracking-tight text-foreground">Snow AI Delivery</p>
        <p className="mt-1 text-sm text-muted-foreground">Photos, users, and upload access.</p>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const isActive = activeTab === (item.href.slice(1) as "reports" | "users");
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMenuOpen(false)}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon className="size-4" />
              {item.label}
            </Link>
          );
        })}

        <button
          type="button"
          onClick={() => {
            setMenuOpen(false);
            setSystemOpen(true);
          }}
          className={cn(
            "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors",
            systemOpen
              ? "bg-sidebar-accent text-sidebar-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          )}
        >
          <Database className="size-4" />
          System
        </button>
      </nav>

      <div className="border-t px-3 py-4">
        <LogoutButton />
      </div>
    </>
  );

  return (
    <main className="min-h-screen bg-background">
      <div className="fixed inset-x-0 top-0 z-40 flex h-14 items-center border-b bg-background/95 px-4 backdrop-blur lg:hidden">
        <Button variant="ghost" size="icon" onClick={() => setMenuOpen((current) => !current)}>
          {menuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
        </Button>
        <div className="ml-3">
          <p className="text-sm font-semibold text-foreground">Snow AI Delivery</p>
          <p className="text-xs text-muted-foreground">{activeTab === "reports" ? "Reports" : "Users"}</p>
        </div>
      </div>

      {menuOpen ? <button className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={() => setMenuOpen(false)} /> : null}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r bg-sidebar transition-transform duration-200 lg:translate-x-0",
          menuOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {sidebarContent}
      </aside>

      <div className="pt-14 lg:pl-64 lg:pt-0">
        <div className="mx-auto min-h-screen max-w-[1800px] p-4 md:p-6 lg:p-8">{children}</div>
      </div>

      {systemOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="surface w-full max-w-lg p-5">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="field-label">System</p>
                <h2 className="mt-1 text-xl font-semibold tracking-tight">Storage status</h2>
              </div>
              <Button size="icon" variant="ghost" onClick={() => setSystemOpen(false)}>
                <X className="size-4" />
              </Button>
            </div>

            <div className="mt-5 grid gap-4">
              <div className="surface p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-foreground">Report database</p>
                  <Badge variant={systemStatus.database.persistent === false ? "warning" : "default"}>
                    {systemStatus.database.label}
                  </Badge>
                </div>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{systemStatus.database.detail}</p>
                {systemStatus.database.warning ? (
                  <p className="mt-2 text-sm font-medium text-red-600">{systemStatus.database.warning}</p>
                ) : null}
              </div>

              <div className="surface p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-foreground">Photo storage</p>
                  <Badge variant="secondary">{systemStatus.photoStorage.label}</Badge>
                </div>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{systemStatus.photoStorage.detail}</p>
              </div>

              {systemError ? (
                <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{systemError}</div>
              ) : null}
            </div>

            <div className="mt-5 flex justify-end">
              <Button variant="outline" onClick={() => setSystemOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  );
}
