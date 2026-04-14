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
