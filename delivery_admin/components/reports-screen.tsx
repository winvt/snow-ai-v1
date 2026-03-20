"use client";

import Image from "next/image";
import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";

import { buildMapUrl, buildPhotoProxyUrl, formatAccuracy, formatBangkokDate, formatCoordinate } from "@/lib/format";
import type { DeliveryLocation, DeliveryReport, ReportsCursor, ReportsResponse } from "@/lib/types";

type FilterState = {
  dateFrom: string;
  dateTo: string;
  customerId: string;
  userId: string;
};

const initialFilters: FilterState = {
  dateFrom: "",
  dateTo: "",
  customerId: "",
  userId: "",
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

export function ReportsScreen() {
  const [locations, setLocations] = useState<DeliveryLocation[]>([]);
  const [selectedLocationIds, setSelectedLocationIds] = useState<string[]>([]);
  const [filters, setFilters] = useState<FilterState>(initialFilters);
  const [reports, setReports] = useState<DeliveryReport[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [statusText, setStatusText] = useState("Loading reports...");
  const [cursor, setCursor] = useState<ReportsCursor | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const selectedReport = useMemo(
    () => reports.find((report) => report.id === selectedReportId) ?? null,
    [reports, selectedReportId]
  );
  const selectedMapUrl = selectedReport ? buildMapUrl(selectedReport.latitude, selectedReport.longitude) : null;

  function buildQuery(
    nextFilters: FilterState = filters,
    nextLocationIds: string[] = selectedLocationIds,
    cursorOverride?: ReportsCursor | null
  ): string {
    const params = new URLSearchParams();
    if (nextFilters.dateFrom) {
      params.set("date_from", nextFilters.dateFrom);
    }
    if (nextFilters.dateTo) {
      params.set("date_to", nextFilters.dateTo);
    }
    if (nextFilters.customerId.trim()) {
      params.set("customer_id", nextFilters.customerId.trim());
    }
    if (nextFilters.userId.trim()) {
      params.set("user_id", nextFilters.userId.trim());
    }
    nextLocationIds.forEach((locationId) => params.append("location_ids", locationId));
    if (cursorOverride?.beforeReceivedAt) {
      params.set("before_received_at", cursorOverride.beforeReceivedAt);
    }
    if (cursorOverride?.beforeId) {
      params.set("before_id", cursorOverride.beforeId);
    }
    return params.toString();
  }

  async function loadLocations() {
    const payload = await fetchJson<{ locations: DeliveryLocation[] }>("/api/admin/locations");
    setLocations(payload.locations);
  }

  async function loadReports(
    reset: boolean,
    options?: {
      filters?: FilterState;
      locationIds?: string[];
    }
  ) {
    if (reset) {
      setLoading(true);
      setStatusText("Loading reports...");
    } else {
      setLoadingMore(true);
    }

    try {
      const query = buildQuery(options?.filters ?? filters, options?.locationIds ?? selectedLocationIds, reset ? null : cursor);
      const payload = await fetchJson<ReportsResponse>(`/api/admin/reports?${query}`);
      const nextReports = reset
        ? payload.reports
        : reports.concat(payload.reports.filter((report) => !reports.some((existing) => existing.id === report.id)));

      setReports(nextReports);
      setCursor(payload.nextCursor);
      setHasMore(Boolean(payload.hasMore));

      if (!nextReports.length) {
        setSelectedReportId(null);
        setStatusText("No reports found for the current filters.");
        return;
      }

      setSelectedReportId((current) => {
        if (current && nextReports.some((report) => report.id === current)) {
          return current;
        }
        return nextReports[0].id;
      });
      setStatusText(`${nextReports.length} report(s) loaded.`);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }

  useEffect(() => {
    void Promise.all([loadLocations(), loadReports(true)]).catch((caughtError) => {
      setStatusText(caughtError instanceof Error ? caughtError.message : "Failed to load reports.");
      setLoading(false);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFilterChange(key: keyof FilterState) {
    return (event: ChangeEvent<HTMLInputElement>) => {
      setFilters((current) => ({
        ...current,
        [key]: event.target.value,
      }));
    };
  }

  function handleLocationToggle(locationId: string) {
    setSelectedLocationIds((current) =>
      current.includes(locationId) ? current.filter((value) => value !== locationId) : current.concat(locationId)
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await loadReports(true);
    } catch (caughtError) {
      setStatusText(caughtError instanceof Error ? caughtError.message : "Failed to load reports.");
    }
  }

  async function handleReset() {
    const clearedFilters = { ...initialFilters };
    setFilters(clearedFilters);
    setSelectedLocationIds([]);
    try {
      await loadReports(true, { filters: clearedFilters, locationIds: [] });
    } catch (caughtError) {
      setStatusText(caughtError instanceof Error ? caughtError.message : "Failed to load reports.");
    }
  }

  async function handleLoadOlder() {
    try {
      await loadReports(false);
    } catch (caughtError) {
      setStatusText(caughtError instanceof Error ? caughtError.message : "Failed to load older reports.");
    }
  }

  return (
    <section className="page-panel">
      <div className="report-screen">
        <aside className="filter-sidebar">
          <form className="filter-form" onSubmit={handleSubmit}>
            <div className="sidebar-section">
              <p className="toolbar-label">Filters</p>
              <p className="sidebar-copy">Keep the full canvas for photos. Use the left rail to narrow the stream.</p>
            </div>

            <div className="sidebar-section">
              <p className="section-title">Locations</p>
              <div className="checklist">
                {locations.map((location) => (
                  <label className="checklist-item" key={location.id}>
                    <input
                      type="checkbox"
                      checked={selectedLocationIds.includes(location.id)}
                      onChange={() => handleLocationToggle(location.id)}
                    />
                    <span>{location.name}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="sidebar-section field-grid">
              <label className="field">
                <span>Date From</span>
                <input type="date" value={filters.dateFrom} onChange={handleFilterChange("dateFrom")} />
              </label>
              <label className="field">
                <span>Date To</span>
                <input type="date" value={filters.dateTo} onChange={handleFilterChange("dateTo")} />
              </label>
              <label className="field">
                <span>Customer ID</span>
                <input type="text" value={filters.customerId} onChange={handleFilterChange("customerId")} placeholder="optional" />
              </label>
              <label className="field">
                <span>LINE User ID</span>
                <input type="text" value={filters.userId} onChange={handleFilterChange("userId")} placeholder="optional" />
              </label>
            </div>

            <div className="sidebar-actions">
              <button className="ghost-button" type="button" onClick={handleReset}>
                Clear
              </button>
              <button className="primary-button" type="submit">
                Load Reports
              </button>
            </div>
          </form>
        </aside>

        <section className="gallery-shell">
          <div className="gallery-header">
            <div>
              <p className="toolbar-label">Recent reports</p>
              <p className="gallery-status">{statusText}</p>
            </div>
          </div>

          <div className="gallery-grid">
            {loading ? <div className="empty-state">Loading latest reports...</div> : null}
            {!loading && !reports.length ? <div className="empty-state">No reports match the active filters.</div> : null}
            {!loading &&
              reports.map((report) => (
                <button
                  key={report.id}
                  className={`photo-card ${report.id === selectedReportId ? "is-active" : ""}`}
                  type="button"
                  onClick={() => setSelectedReportId(report.id)}
                >
                  <div className="photo-card-image">
                    <Image
                      src={buildPhotoProxyUrl(report.photoObjectKey, "thumb")}
                      alt={report.customerName || "Visit photo"}
                      fill
                      sizes="(max-width: 768px) 100vw, (max-width: 1400px) 33vw, 240px"
                    />
                    <span className="photo-card-badge">{report.locationName}</span>
                  </div>
                  <div className="photo-card-copy">
                    <h3>{report.customerName}</h3>
                    <p>{report.userName}</p>
                    <p>{formatBangkokDate(report.capturedAtClient)}</p>
                  </div>
                </button>
              ))}
          </div>

          {hasMore ? (
            <div className="gallery-actions">
              <button className="ghost-button" type="button" onClick={handleLoadOlder} disabled={loadingMore}>
                {loadingMore ? "Loading..." : "Load Older"}
              </button>
            </div>
          ) : null}
        </section>

        <aside className={`detail-drawer ${selectedReport ? "" : "is-empty"}`}>
          {!selectedReport ? (
            <div className="drawer-empty">
              <p className="toolbar-label">Preview</p>
              <h2>Select a report</h2>
              <p>Pick a photo from the stream to inspect the visit details.</p>
            </div>
          ) : (
            <>
              <div className="drawer-head">
                <div>
                  <p className="toolbar-label">Visit detail</p>
                  <h2>{selectedReport.customerName}</h2>
                </div>
                <span className="drawer-location">{selectedReport.locationName}</span>
              </div>

              <a
                className="drawer-image-link"
                href={buildPhotoProxyUrl(selectedReport.photoObjectKey, "original")}
                target="_blank"
                rel="noreferrer"
              >
                <div className="drawer-image-frame">
                  <Image
                    src={buildPhotoProxyUrl(selectedReport.photoObjectKey, "display")}
                    alt={selectedReport.customerName || "Visit photo"}
                    fill
                    sizes="(max-width: 1024px) 100vw, 420px"
                  />
                </div>
              </a>

              <div className="drawer-actions">
                {selectedMapUrl ? (
                  <a className="secondary-button" href={selectedMapUrl} target="_blank" rel="noreferrer">
                    Map
                  </a>
                ) : null}
                <a
                  className="ghost-button"
                  href={buildPhotoProxyUrl(selectedReport.photoObjectKey, "original")}
                  target="_blank"
                  rel="noreferrer"
                >
                  Original
                </a>
              </div>

              <dl className="meta-grid">
                <div>
                  <dt>User</dt>
                  <dd>{selectedReport.userName}</dd>
                </div>
                <div>
                  <dt>Location</dt>
                  <dd>{selectedReport.locationName}</dd>
                </div>
                <div>
                  <dt>Taken</dt>
                  <dd>{formatBangkokDate(selectedReport.capturedAtClient)}</dd>
                </div>
                <div>
                  <dt>Saved</dt>
                  <dd>{formatBangkokDate(selectedReport.receivedAtServer)}</dd>
                </div>
                <div>
                  <dt>Lat</dt>
                  <dd>{formatCoordinate(selectedReport.latitude)}</dd>
                </div>
                <div>
                  <dt>Lng</dt>
                  <dd>{formatCoordinate(selectedReport.longitude)}</dd>
                </div>
                <div>
                  <dt>Acc</dt>
                  <dd>{formatAccuracy(selectedReport.accuracyM)}</dd>
                </div>
                <div>
                  <dt>LINE ID</dt>
                  <dd>{selectedReport.lineUserId}</dd>
                </div>
              </dl>
            </>
          )}
        </aside>
      </div>
    </section>
  );
}
