export function formatBangkokDate(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "-";
  }

  const formatter = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Bangkok",
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour12: false,
  });
  const parts = Object.fromEntries(formatter.formatToParts(parsed).map((part) => [part.type, part.value]));
  return `${parts.hour}:${parts.minute} ${parts.day}/${parts.month}/${parts.year}`;
}

function normalizeNumber(value: number | string | null | undefined): number | null {
  const numeric = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

export function formatCoordinate(value: number | string | null | undefined): string {
  const numeric = normalizeNumber(value);
  return numeric === null ? "-" : numeric.toFixed(5);
}

export function formatAccuracy(value: number | string | null | undefined): string {
  const numeric = normalizeNumber(value);
  return numeric === null ? "-" : `${Math.round(numeric)} m`;
}

export function buildMapUrl(latitude: number | null, longitude: number | null): string | null {
  const lat = normalizeNumber(latitude);
  const lng = normalizeNumber(longitude);
  if (lat === null || lng === null) {
    return null;
  }
  return `https://www.google.com/maps?q=${lat},${lng}`;
}

export function buildPhotoProxyUrl(objectKey: string, variant: "thumb" | "display" | "original"): string {
  const encodedKey = objectKey
    .split("/")
    .map((segment) => encodeURIComponent(segment))
    .join("/");
  return `/api/photos/${encodedKey}?variant=${variant}`;
}
