"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";

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
      const payload = await fetchJson<Pick<DeliveryUserAccess, "accessMode" | "allowedLocationIds"> & { displayName: string; lineUserId: string }>(
        `/api/admin/access/users/${encodeURIComponent(user.lineUserId)}/locations`,
        {
          method: "PUT",
          headers: {
            "content-type": "application/json",
          },
          body: JSON.stringify({
            access_mode: user.draftAccessMode,
            location_ids: user.draftAccessMode === "assigned" ? user.draftLocationIds : [],
          }),
        }
      );

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
    <section className="page-panel">
      <div className="users-screen">
        <header className="users-header">
          <div>
            <p className="toolbar-label">User access</p>
            <p className="gallery-status">{statusText}</p>
          </div>
          <label className="field users-search-field">
            <span>Search user</span>
            <input
              type="search"
              value={search}
              onChange={(event: ChangeEvent<HTMLInputElement>) => setSearch(event.target.value)}
              placeholder="Name or LINE user ID"
            />
          </label>
        </header>

        {!users.length ? <div className="empty-state">No logged-in LINE users yet.</div> : null}
        {users.length && !filteredUsers.length ? <div className="empty-state">No users match this search.</div> : null}

        <div className="users-list">
          {filteredUsers.map((user) => {
            const dirty = isDirty(user);
            const isAssigned = user.draftAccessMode === "assigned";
            return (
              <article className="user-card" key={user.lineUserId}>
                <div className="user-card-head">
                  <div>
                    <div className="user-card-title">
                      <h2>{user.displayName}</h2>
                      <span className="status-pill">{user.status}</span>
                    </div>
                    <p className="user-subline">{user.lineUserId}</p>
                    <p className="user-subline">Last login {formatBangkokDate(user.lastLoginAt)}</p>
                  </div>
                  <span className={`access-pill ${isAssigned ? "is-assigned" : "is-all"}`}>
                    {isAssigned ? "Selected locations" : "All locations"}
                  </span>
                </div>

                <div className="mode-toggle" role="radiogroup" aria-label={`Access mode for ${user.displayName}`}>
                  <label className="mode-option">
                    <input
                      type="radio"
                      name={`access-mode-${user.lineUserId}`}
                      checked={user.draftAccessMode === "all"}
                      onChange={() => handleModeChange(user.lineUserId, "all")}
                    />
                    <span>All locations</span>
                  </label>
                  <label className="mode-option">
                    <input
                      type="radio"
                      name={`access-mode-${user.lineUserId}`}
                      checked={user.draftAccessMode === "assigned"}
                      onChange={() => handleModeChange(user.lineUserId, "assigned")}
                    />
                    <span>Selected locations</span>
                  </label>
                </div>

                <div className={`user-locations ${isAssigned ? "" : "is-disabled"}`}>
                  {locations.map((location) => (
                    <label className="chip-check" key={`${user.lineUserId}-${location.id}`}>
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

                <div className="user-card-footer">
                  <span className={`save-state ${user.saveState === "dirty" ? "is-dirty" : ""} ${user.saveState === "error" ? "is-error" : ""}`}>
                    {user.saveState === "saving"
                      ? "Saving..."
                      : user.saveState === "dirty"
                        ? "Unsaved changes"
                        : user.saveState === "error"
                          ? user.errorMessage || "Save failed"
                          : "Saved"}
                  </span>
                  <button
                    className="primary-button"
                    type="button"
                    disabled={!dirty || user.saveState === "saving"}
                    onClick={() => handleSave(user)}
                  >
                    {user.saveState === "saving" ? "Saving..." : "Save"}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
