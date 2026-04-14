import type { OverviewMetrics } from "./types";

/**
 * Base URL for the Curia API.
 * Configurable via the NEXT_PUBLIC_API_URL environment variable.
 */
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Fetch overview metrics from the API.
 *
 * Returns `null` when the API is unreachable so the dashboard can render
 * a graceful fallback instead of throwing.
 */
export async function fetchOverviewMetrics(): Promise<OverviewMetrics | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/metrics/overview`, {
      next: { revalidate: 60 },
    });

    if (!res.ok) {
      console.error(
        `Failed to fetch overview metrics: ${res.status} ${res.statusText}`,
      );
      return null;
    }

    return (await res.json()) as OverviewMetrics;
  } catch (error) {
    console.error("Failed to fetch overview metrics:", error);
    return null;
  }
}
