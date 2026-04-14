import Link from "next/link";

import { fetchInstitutions, fetchMeetings } from "@/lib/api";
import type { Meeting } from "@/lib/types";
import type { Metadata } from "next";

import { StatusBadge, TypeBadge } from "./_components/badges";

export const metadata: Metadata = {
  title: "Meetings — Curia",
  description:
    "Browse parliamentary sessions and municipal meetings in the Netherlands.",
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

/** Format an ISO datetime string for display. */
function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("nl-NL", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function fmtTime(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" });
}

/** Map meeting status to a coloured badge. */
/* StatusBadge imported from _components/badges */

/* ------------------------------------------------------------------ */
/*  Type badge — national vs municipal                                */
/* ------------------------------------------------------------------ */

/* StatusBadge and TypeBadge are imported from _components/badges */

/* ------------------------------------------------------------------ */
/*  Filters                                                           */
/* ------------------------------------------------------------------ */

function Filters({
  institutions,
  currentInstitutionId,
  currentDateFrom,
  currentDateTo,
  currentView,
}: {
  institutions: { id: string; name: string; institution_type: string }[];
  currentInstitutionId: string;
  currentDateFrom: string;
  currentDateTo: string;
  currentView: string;
}) {
  return (
    <form method="get" className="mb-8 flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end">
      <div className="flex flex-col gap-1">
        <label htmlFor="institutionId" className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
          Institution
        </label>
        <select
          id="institutionId"
          name="institutionId"
          aria-label="Filter by institution"
          defaultValue={currentInstitutionId}
          className="w-full rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm text-zinc-900 focus:border-blue-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 sm:w-56"
        >
          <option value="">All institutions</option>
          {institutions.map((inst) => (
            <option key={inst.id} value={inst.id}>
              {inst.name}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="dateFrom" className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
          From
        </label>
        <input
          id="dateFrom"
          type="date"
          name="dateFrom"
          defaultValue={currentDateFrom}
          aria-label="Start date from"
          className="w-full rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm text-zinc-900 focus:border-blue-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 sm:w-44"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="dateTo" className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
          To
        </label>
        <input
          id="dateTo"
          type="date"
          name="dateTo"
          defaultValue={currentDateTo}
          aria-label="Start date to"
          className="w-full rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm text-zinc-900 focus:border-blue-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 sm:w-44"
        />
      </div>

      {/* Hidden field to preserve current view */}
      <input type="hidden" name="view" value={currentView} />

      <button
        type="submit"
        className="self-end rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
      >
        Filter
      </button>
    </form>
  );
}

/* ------------------------------------------------------------------ */
/*  View toggle                                                       */
/* ------------------------------------------------------------------ */

function ViewToggle({
  currentView,
  searchParams,
}: {
  currentView: string;
  searchParams: Record<string, string>;
}) {
  function href(view: string) {
    const qs = new URLSearchParams(searchParams);
    qs.set("view", view);
    qs.delete("page");
    return `?${qs.toString()}`;
  }

  return (
    <div className="mb-6 flex gap-2">
      <Link
        href={href("list")}
        className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
          currentView === "list"
            ? "bg-blue-600 text-white dark:bg-blue-500"
            : "border border-zinc-300 text-zinc-700 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
        }`}
      >
        List
      </Link>
      <Link
        href={href("calendar")}
        className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
          currentView === "calendar"
            ? "bg-blue-600 text-white dark:bg-blue-500"
            : "border border-zinc-300 text-zinc-700 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
        }`}
      >
        Calendar
      </Link>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Pagination                                                        */
/* ------------------------------------------------------------------ */

function Pagination({
  page,
  pages,
  searchParams,
}: {
  page: number;
  pages: number;
  searchParams: Record<string, string>;
}) {
  if (pages <= 1) return null;

  function href(p: number) {
    const qs = new URLSearchParams(searchParams);
    qs.set("page", String(p));
    return `?${qs.toString()}`;
  }

  return (
    <nav className="mt-8 flex items-center justify-center gap-4">
      {page > 1 ? (
        <Link
          href={href(page - 1)}
          className="rounded-lg border border-zinc-300 px-4 py-2 text-sm hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
        >
          ← Previous
        </Link>
      ) : (
        <span className="rounded-lg border border-zinc-200 px-4 py-2 text-sm text-zinc-400 dark:border-zinc-800">
          ← Previous
        </span>
      )}
      <span className="text-sm text-zinc-600 dark:text-zinc-400">
        Page {page} of {pages}
      </span>
      {page < pages ? (
        <Link
          href={href(page + 1)}
          className="rounded-lg border border-zinc-300 px-4 py-2 text-sm hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
        >
          Next →
        </Link>
      ) : (
        <span className="rounded-lg border border-zinc-200 px-4 py-2 text-sm text-zinc-400 dark:border-zinc-800">
          Next →
        </span>
      )}
    </nav>
  );
}

/* ------------------------------------------------------------------ */
/*  Meeting card                                                      */
/* ------------------------------------------------------------------ */

function MeetingCard({ meeting }: { meeting: Meeting }) {
  return (
    <Link
      href={`/meetings/${meeting.id}`}
      className="group flex flex-col gap-2 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-lg font-semibold text-zinc-900 group-hover:text-blue-600 dark:text-zinc-50 dark:group-hover:text-blue-400">
          {meeting.title ?? "Untitled meeting"}
        </span>
        <StatusBadge status={meeting.status} />
      </div>
      <div className="flex flex-wrap gap-2">
        <TypeBadge meetingType={meeting.meeting_type} />
      </div>
      <div className="flex flex-wrap gap-4 text-sm text-zinc-500 dark:text-zinc-400">
        <span>{fmtDate(meeting.scheduled_start)}</span>
        {meeting.scheduled_start && (
          <span>{fmtTime(meeting.scheduled_start)}</span>
        )}
        {meeting.location && (
          <span>
            <span aria-hidden="true">📍 </span>
            <span className="sr-only">Location: </span>
            {meeting.location}
          </span>
        )}
      </div>
    </Link>
  );
}

/* ------------------------------------------------------------------ */
/*  Calendar view                                                     */
/* ------------------------------------------------------------------ */

function CalendarView({ meetings }: { meetings: Meeting[] }) {
  // Group meetings by date
  const grouped: Record<string, Meeting[]> = {};
  for (const m of meetings) {
    const key = m.scheduled_start
      ? new Date(m.scheduled_start).toISOString().slice(0, 10)
      : "unscheduled";
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(m);
  }

  const sortedDates = Object.keys(grouped).sort((a, b) => a.localeCompare(b));

  if (sortedDates.length === 0) {
    return (
      <p className="text-zinc-500 dark:text-zinc-400">
        No meetings found matching your criteria.
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {sortedDates.map((dateKey) => (
        <div key={dateKey}>
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
            {dateKey === "unscheduled"
              ? "Unscheduled"
              : new Date(dateKey + "T12:00:00Z").toLocaleDateString("nl-NL", {
                  weekday: "long",
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                  timeZone: "UTC",
                })}
          </h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {grouped[dateKey].map((m) => (
              <Link
                key={m.id}
                href={`/meetings/${m.id}`}
                className="group flex flex-col gap-1 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="font-medium text-zinc-900 group-hover:text-blue-600 dark:text-zinc-50 dark:group-hover:text-blue-400">
                    {m.title ?? "Untitled meeting"}
                  </span>
                  <StatusBadge status={m.status} />
                </div>
                <div className="flex flex-wrap gap-2">
                  <TypeBadge meetingType={m.meeting_type} />
                  {m.scheduled_start && (
                    <span className="text-xs text-zinc-400 dark:text-zinc-500">
                      {fmtTime(m.scheduled_start)}
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page (server component)                                           */
/* ------------------------------------------------------------------ */

export default async function MeetingsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const institutionId =
    typeof params.institutionId === "string" ? params.institutionId : "";
  const dateFrom =
    typeof params.dateFrom === "string" ? params.dateFrom : "";
  const dateTo =
    typeof params.dateTo === "string" ? params.dateTo : "";
  const page = Math.max(1, Number(params.page) || 1);
  const view =
    typeof params.view === "string" && params.view === "calendar"
      ? "calendar"
      : "list";

  const [meetingsRes, institutionsRes] = await Promise.all([
    fetchMeetings({
      page,
      institutionId: institutionId || undefined,
      startDateFrom: dateFrom || undefined,
      startDateTo: dateTo || undefined,
    }),
    fetchInstitutions(),
  ]);

  const institutions = (institutionsRes?.items ?? []).map((inst) => ({
    id: inst.id,
    name: inst.name,
    institution_type: inst.institution_type,
  }));

  // Build a plain record of current search params for link construction
  const currentParams: Record<string, string> = {};
  if (institutionId) currentParams.institutionId = institutionId;
  if (dateFrom) currentParams.dateFrom = dateFrom;
  if (dateTo) currentParams.dateTo = dateTo;
  if (view !== "list") currentParams.view = view;

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 font-sans dark:bg-black">
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            href="/"
            className="text-sm text-blue-600 hover:underline dark:text-blue-400"
          >
            ← Dashboard
          </Link>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            Meetings
          </h1>
          <p className="mt-1 text-zinc-600 dark:text-zinc-400">
            Browse parliamentary sessions and municipal meetings.
          </p>
        </div>

        {/* Filters */}
        <Filters
          institutions={institutions}
          currentInstitutionId={institutionId}
          currentDateFrom={dateFrom}
          currentDateTo={dateTo}
          currentView={view}
        />

        {/* View toggle */}
        <ViewToggle currentView={view} searchParams={currentParams} />

        {/* Results */}
        {!meetingsRes ? (
          <p className="text-zinc-500 dark:text-zinc-400">
            Unable to load meetings — the API may be unavailable.
          </p>
        ) : meetingsRes.items.length === 0 ? (
          <p className="text-zinc-500 dark:text-zinc-400">
            No meetings found matching your criteria.
          </p>
        ) : view === "calendar" ? (
          <>
            <p className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
              {meetingsRes.total.toLocaleString("nl-NL")} result
              {meetingsRes.total !== 1 ? "s" : ""}
            </p>
            <CalendarView meetings={meetingsRes.items} />
            <Pagination
              page={meetingsRes.page}
              pages={meetingsRes.pages}
              searchParams={currentParams}
            />
          </>
        ) : (
          <>
            <p className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
              {meetingsRes.total.toLocaleString("nl-NL")} result
              {meetingsRes.total !== 1 ? "s" : ""}
            </p>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {meetingsRes.items.map((m) => (
                <MeetingCard key={m.id} meeting={m} />
              ))}
            </div>
            <Pagination
              page={meetingsRes.page}
              pages={meetingsRes.pages}
              searchParams={currentParams}
            />
          </>
        )}
      </main>
    </div>
  );
}
