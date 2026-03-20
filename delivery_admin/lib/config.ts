function requireEnv(name: string, value: string | undefined): string {
  if (!value || !value.trim()) {
    throw new Error(`${name} is not configured`);
  }
  return value.trim();
}

export function getAdminPassword(): string {
  return requireEnv("ADMIN_PASSWORD", process.env.ADMIN_PASSWORD);
}

export function getAdminSessionSecret(): string {
  return requireEnv("ADMIN_SESSION_SECRET", process.env.ADMIN_SESSION_SECRET);
}

export function getAdminInternalApiToken(): string {
  return requireEnv("ADMIN_INTERNAL_API_TOKEN", process.env.ADMIN_INTERNAL_API_TOKEN);
}

export function getDeliveryApiBaseUrl(): string {
  return requireEnv("DELIVERY_API_BASE_URL", process.env.DELIVERY_API_BASE_URL).replace(/\/+$/, "");
}
