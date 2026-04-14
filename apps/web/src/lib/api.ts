import type {
  Mandate,
  OverviewMetrics,
  PaginatedResponse,
  Party,
  Politician,
} from "./types";

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

/**
 * Fetch a paginated list of politicians.
 */
export async function fetchPoliticians(params: {
  page?: number;
  search?: string;
  partyId?: string;
}): Promise<PaginatedResponse<Politician> | null> {
  try {
    const limit = 20;
    const offset = ((params.page ?? 1) - 1) * limit;
    const qs = new URLSearchParams();
    qs.set("limit", String(limit));
    qs.set("offset", String(offset));
    if (params.search) qs.set("full_name", params.search);
    if (params.partyId) qs.set("party_id", params.partyId);

    const res = await fetch(
      `${API_BASE_URL}/api/v1/politicians?${qs.toString()}`,
      { next: { revalidate: 60 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as PaginatedResponse<Politician>;
  } catch {
    return null;
  }
}

/**
 * Fetch a single politician by ID.
 */
export async function fetchPolitician(
  id: string,
): Promise<Politician | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/politicians/${id}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return (await res.json()) as Politician;
  } catch {
    return null;
  }
}

/**
 * Fetch mandates (committee memberships, party roles) for a politician.
 */
export async function fetchPoliticianMandates(
  politicianId: string,
): Promise<PaginatedResponse<Mandate> | null> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/politicians/${politicianId}/mandates?limit=100`,
      { next: { revalidate: 60 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as PaginatedResponse<Mandate>;
  } catch {
    return null;
  }
}

/**
 * Fetch all parties (for filter dropdowns).
 */
export async function fetchParties(): Promise<PaginatedResponse<Party> | null> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/parties?limit=100`,
      { next: { revalidate: 300 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as PaginatedResponse<Party>;
  } catch {
    return null;
  }
}
