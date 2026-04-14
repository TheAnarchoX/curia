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

/** A political institution returned by GET /api/v1/institutions. */
export interface Institution {
  id: string;
  jurisdiction_id: string;
  name: string;
  slug: string;
  institution_type: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

/** A meeting returned by GET /api/v1/meetings. */
export interface Meeting {
  id: string;
  governing_body_id: string;
  title: string | null;
  meeting_type: string | null;
  scheduled_start: string | null;
  scheduled_end: string | null;
  status: string;
  location: string | null;
  source_url: string | null;
  created_at: string;
  updated_at: string;
}

/** An agenda item returned by GET /api/v1/agenda-items. */
export interface AgendaItem {
  id: string;
  meeting_id: string;
  ordering: number;
  title: string;
  description: string | null;
  parent_item_id: string | null;
  created_at: string;
  updated_at: string;
}

/** A document returned by GET /api/v1/documents. */
export interface Document {
  id: string;
  title: string | null;
  document_type: string;
  source_url: string | null;
  mime_type: string | null;
  text_extracted: boolean;
  page_count: number | null;
  meeting_id: string | null;
  agenda_item_id: string | null;
  created_at: string;
  updated_at: string;
}

/** A vote returned by GET /api/v1/votes. */
export interface Vote {
  id: string;
  decision_id: string;
  proposition_type: string | null;
  proposition_id: string | null;
  date: string | null;
  outcome: string | null;
  votes_for: number | null;
  votes_against: number | null;
  votes_abstain: number | null;
  created_at: string;
  updated_at: string;
}

/** A decision returned by GET /api/v1/decisions. */
export interface Decision {
  id: string;
  meeting_id: string;
  agenda_item_id: string | null;
  decision_type: string;
  outcome: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}
