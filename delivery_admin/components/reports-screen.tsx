"use client";

import Image from "next/image";
import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { CalendarDays, ChevronDown, MapPinned, Search, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { buildMapUrl, buildPhotoProxyUrl, formatAccuracy, formatBangkokDate, formatCoordinate } from "../lib/format";
import type { DeliveryLocation, DeliveryReport, ReportsCursor, ReportsResponse } from "../lib/types";

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
  const [locationSearch, setLocationSearch] = useState("");
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
  const visibleLocations = useMemo(() => {
    const token = locationSearch.trim().toLowerCase();
    if (!token) {
      return locations;
    }
    return locations.filter((location) => location.name.toLowerCase().includes(token));
  }, [locationSearch, locations]);

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
    setLocationSearch("");
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
    <section className="space-y-4">
      <header className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Reports</h1>
          <p className="mt-1 text-sm text-muted-foreground">{statusText}</p>
        </div>
        <Badge variant="secondary">{reports.length} loaded</Badge>
      </header>

      <div
        className={cn(
          "grid gap-4 xl:items-start",
          selectedReport ? "xl:grid-cols-[280px_minmax(0,1fr)_360px]" : "xl:grid-cols-[280px_minmax(0,1fr)]"
        )}
      >
        <aside className="surface p-4 xl:sticky xl:top-8">
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <p className="field-label">Filters</p>
              <p className="mt-1 text-sm text-muted-foreground">Use the left rail to narrow the photo stream.</p>
            </div>

            <details className="rounded-lg border bg-background" open>
              <summary className="flex cursor-pointer items-center justify-between px-3 py-2 text-sm font-medium text-foreground">
                <span>Locations</span>
                <ChevronDown className="size-4 text-muted-foreground" />
              </summary>
              <div className="space-y-3 border-t px-3 py-3">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    className="pl-9"
                    type="search"
                    value={locationSearch}
                    onChange={(event) => setLocationSearch(event.target.value)}
                    placeholder="Search location"
                  />
                </div>
                <div className="max-h-72 space-y-2 overflow-y-auto pr-1 scrollbar-thin">
                  {visibleLocations.map((location) => (
                    <label
                      className="flex items-start gap-3 rounded-md px-2 py-2 text-sm text-foreground hover:bg-muted"
                      key={location.id}
                    >
                      <input
                        className="mt-1 size-4 rounded border-input text-primary"
                        type="checkbox"
                        checked={selectedLocationIds.includes(location.id)}
                        onChange={() => handleLocationToggle(location.id)}
                      />
                      <span className="leading-5">{location.name}</span>
                    </label>
                  ))}
                  {!visibleLocations.length ? <p className="px-2 py-3 text-sm text-muted-foreground">No locations match.</p> : null}
                </div>
              </div>
            </details>

            <details className="rounded-lg border bg-background" open>
              <summary className="flex cursor-pointer items-center justify-between px-3 py-2 text-sm font-medium text-foreground">
                <span>Date</span>
                <ChevronDown className="size-4 text-muted-foreground" />
              </summary>
              <div className="grid gap-3 border-t px-3 py-3">
                <label className="grid gap-2">
                  <span className="field-label">Date From</span>
                  <div className="relative">
                    <CalendarDays className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                    <Input type="date" value={filters.dateFrom} onChange={handleFilterChange("dateFrom")} />
                  </div>
                </label>
                <label className="grid gap-2">
                  <span className="field-label">Date To</span>
                  <div className="relative">
                    <CalendarDays className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                    <Input type="date" value={filters.dateTo} onChange={handleFilterChange("dateTo")} />
                  </div>
                </label>
              </div>
            </details>

            <div className="grid gap-3">
              <label className="grid gap-2">
                <span className="field-label">Customer ID</span>
                <Input type="text" value={filters.customerId} onChange={handleFilterChange("customerId")} placeholder="optional" />
              </label>
              <label className="grid gap-2">
                <span className="field-label">LINE User ID</span>
                <Input type="text" value={filters.userId} onChange={handleFilterChange("userId")} placeholder="optional" />
              </label>
            </div>

            <div className="flex items-center gap-2">
              <Button className="flex-1" type="submit">
                Apply
              </Button>
              <Button type="button" variant="outline" onClick={handleReset}>
                Reset
              </Button>
            </div>
          </form>
        </aside>

        <section className="space-y-4 min-w-0">
          {!loading && !reports.length ? (
            <Card>
              <CardContent className="p-8 text-center text-sm text-muted-foreground">No reports match the active filters.</CardContent>
            </Card>
          ) : null}

          {loading ? (
            <Card>
              <CardContent className="p-8 text-center text-sm text-muted-foreground">Loading latest reports...</CardContent>
            </Card>
          ) : null}

          <div
            className={cn(
              "grid gap-3",
              selectedReport
                ? "grid-cols-2 md:grid-cols-3 2xl:grid-cols-4"
                : "grid-cols-2 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5"
            )}
          >
            {!loading &&
              reports.map((report) => (
                <button
                  key={report.id}
                  className={cn(
                    "group overflow-hidden rounded-xl border bg-card text-left shadow-sm transition hover:border-primary/40 hover:shadow-md",
                    report.id === selectedReportId ? "border-primary ring-1 ring-primary/20" : "border-border"
                  )}
                  type="button"
                  onClick={() => setSelectedReportId(report.id)}
                >
                  <div className="relative aspect-[4/3] overflow-hidden bg-muted">
                    <Image
                      src={buildPhotoProxyUrl(report.photoObjectKey, "thumb")}
                      alt={report.customerName || "Visit photo"}
                      fill
                      sizes="(max-width: 768px) 50vw, (max-width: 1536px) 25vw, 18vw"
                      className="object-cover transition-transform duration-200 group-hover:scale-[1.02]"
                    />
                    <span className="absolute left-2 top-2 rounded-md bg-background/90 px-2 py-1 text-[11px] font-medium text-foreground shadow-sm">
                      {report.locationName}
                    </span>
                  </div>
                  <div className="space-y-1 px-3 py-3">
                    <h3 className="truncate text-sm font-semibold text-foreground">{report.customerName}</h3>
                    <p className="truncate text-xs text-muted-foreground">{formatBangkokDate(report.capturedAtClient)}</p>
                  </div>
                </button>
              ))}
          </div>

          {hasMore ? (
            <div className="flex justify-center">
              <Button type="button" variant="outline" onClick={handleLoadOlder} disabled={loadingMore}>
                {loadingMore ? "Loading..." : "Load Older"}
              </Button>
            </div>
          ) : null}
        </section>

        {selectedReport ? (
          <aside className="surface p-4 xl:sticky xl:top-8">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="field-label">Report detail</p>
                <h2 className="mt-1 text-lg font-semibold tracking-tight text-foreground">{selectedReport.customerName}</h2>
              </div>
              <Button size="icon" variant="ghost" onClick={() => setSelectedReportId(null)}>
                <X className="size-4" />
              </Button>
            </div>

            <div className="mt-4 overflow-hidden rounded-xl border bg-muted">
              <a href={buildPhotoProxyUrl(selectedReport.photoObjectKey, "original")} target="_blank" rel="noreferrer">
                <div className="relative aspect-[4/3]">
                  <Image
                    src={buildPhotoProxyUrl(selectedReport.photoObjectKey, "display")}
                    alt={selectedReport.customerName || "Visit photo"}
                    fill
                    sizes="(max-width: 1280px) 100vw, 360px"
                    className="object-cover"
                  />
                </div>
              </a>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-2">
              {selectedMapUrl ? (
                <Button onClick={() => window.open(selectedMapUrl, "_blank", "noreferrer")}>
                  <MapPinned className="size-4" />
                  Map
                </Button>
              ) : null}
              <Button
                variant="outline"
                onClick={() => window.open(buildPhotoProxyUrl(selectedReport.photoObjectKey, "original"), "_blank", "noreferrer")}
              >
                Original
              </Button>
            </div>

            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle>User</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 text-sm">
                  <p className="font-medium text-foreground">{selectedReport.userName}</p>
                  <p className="break-all text-muted-foreground">{selectedReport.lineUserId}</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle>Location</CardTitle>
                </CardHeader>
                <CardContent className="text-sm font-medium text-foreground">{selectedReport.locationName}</CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle>Taken</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-foreground">{formatBangkokDate(selectedReport.capturedAtClient)}</CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle>Saved</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-foreground">{formatBangkokDate(selectedReport.receivedAtServer)}</CardContent>
              </Card>

              <Card className="sm:col-span-2 xl:col-span-1 2xl:col-span-2">
                <CardHeader className="pb-2">
                  <CardTitle>GPS</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-2 text-sm sm:grid-cols-3">
                  <div>
                    <p className="field-label">Lat</p>
                    <p className="mt-1 text-foreground">{formatCoordinate(selectedReport.latitude)}</p>
                  </div>
                  <div>
                    <p className="field-label">Lng</p>
                    <p className="mt-1 text-foreground">{formatCoordinate(selectedReport.longitude)}</p>
                  </div>
                  <div>
                    <p className="field-label">Acc</p>
                    <p className="mt-1 text-foreground">{formatAccuracy(selectedReport.accuracyM)}</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </aside>
        ) : null}
      </div>
    </section>
  );
}
