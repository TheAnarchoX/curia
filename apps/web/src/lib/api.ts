import type {
  AgendaItem,
  Document,
  Institution,
  Mandate,
  Meeting,
  OverviewMetrics,
  PaginatedResponse,
  Party,
  Politician,
  Vote,
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

/**
 * Fetch all institutions (for filter dropdowns).
 */
export async function fetchInstitutions(): Promise<PaginatedResponse<Institution> | null> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/institutions?limit=100`,
      { next: { revalidate: 300 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as PaginatedResponse<Institution>;
  } catch {
    return null;
  }
}

/**
 * Fetch a paginated list of meetings.
 */
export async function fetchMeetings(params: {
  page?: number;
  institutionId?: string;
  startDateFrom?: string;
  startDateTo?: string;
  status?: string;
}): Promise<PaginatedResponse<Meeting> | null> {
  try {
    const limit = 20;
    const offset = ((params.page ?? 1) - 1) * limit;
    const qs = new URLSearchParams();
    qs.set("limit", String(limit));
    qs.set("offset", String(offset));
    if (params.institutionId) qs.set("institution_id", params.institutionId);
    if (params.startDateFrom) qs.set("start_date_from", params.startDateFrom);
    if (params.startDateTo) qs.set("start_date_to", params.startDateTo);
    if (params.status) qs.set("status", params.status);

    const res = await fetch(
      `${API_BASE_URL}/api/v1/meetings?${qs.toString()}`,
      { next: { revalidate: 60 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as PaginatedResponse<Meeting>;
  } catch {
    return null;
  }
}

/**
 * Fetch a single meeting by ID.
 */
export async function fetchMeeting(id: string): Promise<Meeting | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/meetings/${id}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return (await res.json()) as Meeting;
  } catch {
    return null;
  }
}

/**
 * Fetch agenda items for a meeting.
 */
export async function fetchAgendaItems(
  meetingId: string,
): Promise<PaginatedResponse<AgendaItem> | null> {
  if (!meetingId || meetingId.trim().length === 0) return null;

  try {
    const qs = new URLSearchParams({
      meeting_id: meetingId,
      limit: "100",
    });
    const res = await fetch(
      `${API_BASE_URL}/api/v1/agenda-items?${qs.toString()}`,
      { next: { revalidate: 60 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as PaginatedResponse<AgendaItem>;
  } catch {
    return null;
  }
}

/**
 * Fetch documents for a meeting.
 */
export async function fetchDocuments(
  meetingId: string,
): Promise<PaginatedResponse<Document> | null> {
  if (!meetingId || meetingId.trim().length === 0) return null;

  try {
    const qs = new URLSearchParams({
      meeting_id: meetingId,
      limit: "100",
    });
    const res = await fetch(
      `${API_BASE_URL}/api/v1/documents?${qs.toString()}`,
      { next: { revalidate: 60 } },
    );
    if (!res.ok) return null;
    return (await res.json()) as PaginatedResponse<Document>;
  } catch {
    return null;
  }
}

/**
 * Return an empty vote result for meeting detail pages.
 *
 * The current API exposes votes filtered by decision_id, but does not provide
 * a direct meeting_id filter or a meeting-to-decision lookup endpoint. Until
 * that exists, meeting pages render a placeholder and this helper returns a
 * stable empty response.
 */
export async function fetchVotesForMeeting(
  _meetingId: string,
): Promise<PaginatedResponse<Vote> | null> {
  // The votes API does not have a meeting_id filter.
  // Return empty to avoid errors; the UI will show a placeholder.
  return { items: [], total: 0, page: 1, page_size: 0, pages: 0 };
}
