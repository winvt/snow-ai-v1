"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { formatBangkokDate } from "../lib/format";
import type { DeliveryLocation, DeliveryUserAccess } from "../lib/types";

type DraftUser = DeliveryUserAccess & {
  draftAccessMode: "all" | "assigned";
  draftLocationIds: string[];
  saveState: "saved" | "dirty" | "saving" | "error";
  errorMessage?: string;
};

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    cache: "no-store",
  });
  const payload = (await response.json().catch(() => ({}))) as T & { detail?: string };
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed.");
  }
  return payload;
}

function isDirty(user: DraftUser): boolean {
  const expectedIds = user.accessMode === "assigned" ? user.allowedLocationIds.slice().sort().join(",") : "";
  const draftIds = user.draftAccessMode === "assigned" ? user.draftLocationIds.slice().sort().join(",") : "";
  return user.accessMode !== user.draftAccessMode || expectedIds !== draftIds;
}

function buildDraftUsers(users: DeliveryUserAccess[]): DraftUser[] {
  return users.map((user) => ({
    ...user,
    draftAccessMode: user.accessMode,
    draftLocationIds: user.allowedLocationIds.slice().sort(),
    saveState: "saved",
  }));
}

export function UsersScreen() {
  const [locations, setLocations] = useState<DeliveryLocation[]>([]);
  const [users, setUsers] = useState<DraftUser[]>([]);
  const [search, setSearch] = useState("");
  const [statusText, setStatusText] = useState("Loading users...");

  useEffect(() => {
    void Promise.all([
      fetchJson<{ locations: DeliveryLocation[] }>("/api/admin/locations"),
      fetchJson<{ users: DeliveryUserAccess[] }>("/api/admin/access/users"),
    ])
      .then(([locationPayload, userPayload]) => {
        setLocations(locationPayload.locations);
        setUsers(buildDraftUsers(userPayload.users));
        setStatusText(
          userPayload.users.length ? `${userPayload.users.length} user(s) loaded.` : "No logged-in users yet."
        );
      })
      .catch((caughtError) => {
        setStatusText(caughtError instanceof Error ? caughtError.message : "Failed to load users.");
      });
  }, []);

  const filteredUsers = useMemo(() => {
    const token = search.trim().toLowerCase();
    if (!token) {
      return users;
    }
    return users.filter((user) => {
      return user.displayName.toLowerCase().includes(token) || user.lineUserId.toLowerCase().includes(token);
    });
  }, [search, users]);

  useEffect(() => {
    if (!users.length) {
      return;
    }
    setStatusText(search.trim() ? `${filteredUsers.length} of ${users.length} user(s)` : `${users.length} user(s) loaded.`);
  }, [filteredUsers.length, search, users.length]);

  function updateUser(lineUserId: string, updater: (user: DraftUser) => DraftUser) {
    setUsers((current) =>
      current.map((user) => {
        if (user.lineUserId !== lineUserId) {
          return user;
        }
        const nextUser = updater(user);
        return {
          ...nextUser,
          saveState: nextUser.saveState === "saving" ? "saving" : isDirty(nextUser) ? "dirty" : "saved",
        };
      })
    );
  }

  function handleModeChange(lineUserId: string, accessMode: "all" | "assigned") {
    updateUser(lineUserId, (user) => ({
      ...user,
      draftAccessMode: accessMode,
    }));
  }

  function handleLocationToggle(lineUserId: string, locationId: string) {
    updateUser(lineUserId, (user) => {
      const nextIds = user.draftLocationIds.includes(locationId)
        ? user.draftLocationIds.filter((value) => value !== locationId)
        : user.draftLocationIds.concat(locationId).sort();
      return {
        ...user,
        draftLocationIds: nextIds,
      };
    });
  }

  async function handleSave(user: DraftUser) {
    updateUser(user.lineUserId, (current) => ({
      ...current,
      saveState: "saving",
      errorMessage: "",
    }));
    try {
      const payload = await fetchJson<
        Pick<DeliveryUserAccess, "accessMode" | "allowedLocationIds"> & { displayName: string; lineUserId: string }
      >(`/api/admin/access/users/${encodeURIComponent(user.lineUserId)}/locations`, {
        method: "PUT",
        headers: {
          "content-type": "application/json",
        },
        body: JSON.stringify({
          access_mode: user.draftAccessMode,
          location_ids: user.draftAccessMode === "assigned" ? user.draftLocationIds : [],
        }),
      });

      setUsers((current) =>
        current.map((candidate) =>
          candidate.lineUserId === user.lineUserId
            ? {
                ...candidate,
                accessMode: payload.accessMode,
                allowedLocationIds: payload.allowedLocationIds,
                draftAccessMode: payload.accessMode,
                draftLocationIds: payload.allowedLocationIds.slice().sort(),
                saveState: "saved",
                errorMessage: "",
              }
            : candidate
        )
      );
      setStatusText(`Saved ${user.displayName}.`);
    } catch (caughtError) {
      const message = caughtError instanceof Error ? caughtError.message : "Failed to save user access.";
      setUsers((current) =>
        current.map((candidate) =>
          candidate.lineUserId === user.lineUserId
            ? {
                ...candidate,
                saveState: "error",
                errorMessage: message,
              }
            : candidate
        )
      );
      setStatusText(message);
    }
  }

  return (
    <section className="space-y-4">
      <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Users</h1>
          <p className="mt-1 text-sm text-muted-foreground">{statusText}</p>
        </div>
        <label className="grid gap-2 md:w-80">
          <span className="field-label">Search user</span>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-9"
              type="search"
              value={search}
              onChange={(event: ChangeEvent<HTMLInputElement>) => setSearch(event.target.value)}
              placeholder="Name or LINE user ID"
            />
          </div>
        </label>
      </header>

      {!users.length ? (
        <Card>
          <CardContent className="p-8 text-center text-sm text-muted-foreground">No logged-in LINE users yet.</CardContent>
        </Card>
      ) : null}

      {users.length && !filteredUsers.length ? (
        <Card>
          <CardContent className="p-8 text-center text-sm text-muted-foreground">No users match this search.</CardContent>
        </Card>
      ) : null}

      {filteredUsers.length ? (
        <div className="overflow-hidden rounded-xl border bg-card shadow-sm">
          <div className="hidden border-b bg-muted/40 px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground lg:grid lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1.2fr)_240px_200px] lg:gap-4">
            <span>User</span>
            <span>LINE ID</span>
            <span>Access</span>
            <span className="text-right">Actions</span>
          </div>

          <div className="divide-y">
            {filteredUsers.map((user) => {
              const dirty = isDirty(user);
              const isAssigned = user.draftAccessMode === "assigned";
              return (
                <article className="px-4 py-4" key={user.lineUserId}>
                  <div className="grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1.2fr)_240px_200px] lg:items-start">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="text-sm font-semibold text-foreground">{user.displayName}</h2>
                        <Badge variant="secondary">{user.status}</Badge>
                        <Badge variant={isAssigned ? "default" : "outline"}>
                          {isAssigned ? `${user.draftLocationIds.length} locations` : "All locations"}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground">Last login {formatBangkokDate(user.lastLoginAt)}</p>
                    </div>

                    <div className="break-all text-sm text-muted-foreground">{user.lineUserId}</div>

                    <div className="grid gap-2">
                      <label className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
                        <input
                          type="radio"
                          name={`access-mode-${user.lineUserId}`}
                          checked={user.draftAccessMode === "all"}
                          onChange={() => handleModeChange(user.lineUserId, "all")}
                        />
                        <span>All locations</span>
                      </label>
                      <label className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
                        <input
                          type="radio"
                          name={`access-mode-${user.lineUserId}`}
                          checked={user.draftAccessMode === "assigned"}
                          onChange={() => handleModeChange(user.lineUserId, "assigned")}
                        />
                        <span>Selected locations</span>
                      </label>
                    </div>

                    <div className="flex items-center justify-between gap-3 lg:justify-end">
                      <span
                        className={cn(
                          "text-xs font-medium",
                          user.saveState === "error"
                            ? "text-red-600"
                            : user.saveState === "dirty"
                              ? "text-amber-600"
                              : "text-muted-foreground"
                        )}
                      >
                        {user.saveState === "saving"
                          ? "Saving..."
                          : user.saveState === "dirty"
                            ? "Unsaved changes"
                            : user.saveState === "error"
                              ? user.errorMessage || "Save failed"
                              : "Saved"}
                      </span>
                      <Button disabled={!dirty || user.saveState === "saving"} onClick={() => handleSave(user)}>
                        {user.saveState === "saving" ? "Saving..." : "Save"}
                      </Button>
                    </div>
                  </div>

                  <div className="mt-4 space-y-2">
                    <p className="field-label">Locations</p>
                    <div className={cn("flex flex-wrap gap-2", !isAssigned && "opacity-60")}>
                      {locations.map((location) => (
                        <label
                          className={cn(
                            "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm",
                            user.draftLocationIds.includes(location.id) ? "border-primary bg-primary/5 text-primary" : "text-foreground"
                          )}
                          key={`${user.lineUserId}-${location.id}`}
                        >
                          <input
                            type="checkbox"
                            checked={user.draftLocationIds.includes(location.id)}
                            disabled={!isAssigned}
                            onChange={() => handleLocationToggle(user.lineUserId, location.id)}
                          />
                          <span>{location.name}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      ) : null}
    </section>
  );
}
