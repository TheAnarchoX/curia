import Link from "next/link";
import { notFound } from "next/navigation";

import {
  fetchAgendaItems,
  fetchDocuments,
  fetchMeeting,
  fetchVotesForMeeting,
} from "@/lib/api";
import type { AgendaItem, Document, Vote } from "@/lib/types";
import type { Metadata } from "next";

import { StatusBadge, TypeBadge } from "../_components/badges";

/* ------------------------------------------------------------------ */
/*  Dynamic metadata for SEO                                          */
/* ------------------------------------------------------------------ */

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const meeting = await fetchMeeting(id);

  if (!meeting) {
    return { title: "Meeting not found — Curia" };
  }

  return {
    title: `${meeting.title ?? "Meeting"} — Curia`,
    description: `Details for meeting: ${meeting.title ?? meeting.id}.`,
  };
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                           */
/* ------------------------------------------------------------------ */

function fmtDatetime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("nl-NL", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function InfoRow({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <div className="flex gap-2 text-sm">
      <span className="font-medium text-zinc-500 dark:text-zinc-400">
        {label}:
      </span>
      <span className="text-zinc-900 dark:text-zinc-100">{value}</span>
    </div>
  );
}

/* StatusBadge and TypeBadge imported from _components/badges */

/* ------------------------------------------------------------------ */
/*  Agenda items section                                              */
/* ------------------------------------------------------------------ */

function AgendaItemCard({ item }: { item: AgendaItem }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-start gap-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700 dark:bg-blue-900 dark:text-blue-300">
          {item.ordering}
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-medium text-zinc-900 dark:text-zinc-100">
            {item.title}
          </p>
          {item.description && (
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
              {item.description}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Documents section                                                 */
/* ------------------------------------------------------------------ */

function DocumentCard({ doc }: { doc: Document }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="font-medium text-zinc-900 dark:text-zinc-100">
            {doc.title ?? "Untitled document"}
          </p>
          <div className="mt-1 flex flex-wrap gap-2 text-xs text-zinc-500 dark:text-zinc-400">
            <span className="rounded bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800">
              {doc.document_type}
            </span>
            {doc.mime_type && <span>{doc.mime_type}</span>}
            {doc.page_count != null && (
              <span>{doc.page_count} page{doc.page_count !== 1 ? "s" : ""}</span>
            )}
          </div>
        </div>
        {doc.source_url && (
          <a
            href={doc.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 text-sm text-blue-600 hover:underline dark:text-blue-400"
          >
            View ↗
          </a>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Votes section                                                     */
/* ------------------------------------------------------------------ */

function VoteCard({ vote }: { vote: Vote }) {
  const outcomeColour: Record<string, string> = {
    adopted: "text-green-700 dark:text-green-400",
    rejected: "text-red-700 dark:text-red-400",
    tied: "text-yellow-700 dark:text-yellow-400",
    not_voted: "text-zinc-500 dark:text-zinc-400",
  };
  const outcomeLabel: Record<string, string> = {
    adopted: "Adopted",
    rejected: "Rejected",
    tied: "Tied",
    not_voted: "Not voted",
  };

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-center justify-between gap-2">
        <span
          className={`text-sm font-semibold ${outcomeColour[vote.outcome ?? ""] ?? "text-zinc-700 dark:text-zinc-300"}`}
        >
          {outcomeLabel[vote.outcome ?? ""] ?? "Unknown outcome"}
        </span>
        {vote.date && (
          <span className="text-xs text-zinc-400 dark:text-zinc-500">
            {vote.date}
          </span>
        )}
      </div>
      <div className="mt-2 flex gap-4 text-sm text-zinc-600 dark:text-zinc-400">
        {vote.votes_for != null && <span>For: {vote.votes_for}</span>}
        {vote.votes_against != null && (
          <span>Against: {vote.votes_against}</span>
        )}
        {vote.votes_abstain != null && (
          <span>Abstain: {vote.votes_abstain}</span>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page (server component)                                           */
/* ------------------------------------------------------------------ */

export default async function MeetingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [meeting, agendaRes, docsRes, votesRes] = await Promise.all([
    fetchMeeting(id),
    fetchAgendaItems(id),
    fetchDocuments(id),
    fetchVotesForMeeting(id),
  ]);

  if (!meeting) {
    notFound();
  }

  const agendaItems = agendaRes?.items ?? [];
  const documents = docsRes?.items ?? [];
  const votes = votesRes?.items ?? [];

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 font-sans dark:bg-black">
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <div className="mb-8">
          <Link
            href="/meetings"
            className="text-sm text-blue-600 hover:underline dark:text-blue-400"
          >
            ← Meetings
          </Link>
        </div>

        {/* Meeting header */}
        <section className="mb-10">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            {meeting.title ?? "Untitled meeting"}
          </h1>
          <div className="mt-3 flex flex-wrap gap-2">
            <StatusBadge status={meeting.status} />
            <TypeBadge meetingType={meeting.meeting_type} verbose />
          </div>
          <div className="mt-4 flex flex-col gap-1">
            <InfoRow label="Start" value={fmtDatetime(meeting.scheduled_start)} />
            <InfoRow label="End" value={fmtDatetime(meeting.scheduled_end)} />
            <InfoRow label="Location" value={meeting.location} />
          </div>
          {meeting.source_url && (
            <a
              href={meeting.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-block text-sm text-blue-600 hover:underline dark:text-blue-400"
            >
              View source ↗
            </a>
          )}
        </section>

        {/* Agenda items */}
        <section className="mb-10">
          <h2 className="mb-4 text-xl font-semibold text-zinc-800 dark:text-zinc-200">
            Agenda items
          </h2>
          {agendaItems.length === 0 ? (
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              No agenda items recorded for this meeting.
            </p>
          ) : (
            <div className="space-y-3">
              {agendaItems.map((item) => (
                <AgendaItemCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </section>

        {/* Documents */}
        <section className="mb-10">
          <h2 className="mb-4 text-xl font-semibold text-zinc-800 dark:text-zinc-200">
            Documents
          </h2>
          {documents.length === 0 ? (
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              No documents associated with this meeting.
            </p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {documents.map((doc) => (
                <DocumentCard key={doc.id} doc={doc} />
              ))}
            </div>
          )}
        </section>

        {/* Votes */}
        <section>
          <h2 className="mb-4 text-xl font-semibold text-zinc-800 dark:text-zinc-200">
            Votes
          </h2>
          {votes.length === 0 ? (
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              Vote data for this meeting will appear here once ingested.
            </p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {votes.map((v) => (
                <VoteCard key={v.id} vote={v} />
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
