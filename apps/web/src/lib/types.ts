/** High-level entity counts returned by GET /api/v1/metrics/overview. */
export interface OverviewMetrics {
  meetings: number;
  politicians: number;
  parties: number;
  motions: number;
  votes: number;
  documents: number;
  amendments: number;
  written_questions: number;
}

/** Generic paginated list response from the API. */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/** A politician returned by GET /api/v1/politicians. */
export interface Politician {
  id: string;
  full_name: string;
  given_name: string | null;
  family_name: string | null;
  initials: string | null;
  aliases: string[];
  gender: string | null;
  date_of_birth: string | null;
  created_at: string;
  updated_at: string;
}

/** A political party returned by GET /api/v1/parties. */
export interface Party {
  id: string;
  name: string;
  abbreviation: string | null;
  aliases: string[];
  scope_level: string | null;
  active_from: string | null;
  active_until: string | null;
  created_at: string;
  updated_at: string;
}

/** A mandate linking a politician to a role, returned by GET /api/v1/politicians/{id}/mandates. */
export interface Mandate {
  id: string;
  politician_id: string;
  party_id: string | null;
  institution_id: string | null;
  governing_body_id: string | null;
  role: string;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
  updated_at: string;
}
