import Link from "next/link";
import { notFound } from "next/navigation";

import {
  fetchParties,
  fetchPolitician,
  fetchPoliticianMandates,
} from "@/lib/api";
import type { Mandate, Politician } from "@/lib/types";
import type { Metadata } from "next";

/* ------------------------------------------------------------------ */
/*  Dynamic metadata for SEO                                          */
/* ------------------------------------------------------------------ */

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const politician = await fetchPolitician(id);

  if (!politician) {
    return { title: "Politician not found — Curia" };
  }

  return {
    title: `${politician.full_name} — Curia`,
    description: `Profile and committee memberships for ${politician.full_name}.`,
  };
}

/* ------------------------------------------------------------------ */
/*  Info row helper                                                    */
/* ------------------------------------------------------------------ */

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

/* ------------------------------------------------------------------ */
/*  Mandate card                                                      */
/* ------------------------------------------------------------------ */

function MandateCard({
  mandate,
  partyNames,
}: {
  mandate: Mandate;
  partyNames: Record<string, string>;
}) {
  const dateRange = mandate.start_date
    ? `${mandate.start_date} — ${mandate.end_date ?? "present"}`
    : mandate.end_date ?? "";

  const partyLabel = mandate.party_id
    ? partyNames[mandate.party_id] ?? mandate.party_id
    : null;

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-start justify-between gap-2">
        <span className="inline-block rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800 dark:bg-blue-900 dark:text-blue-200">
          {mandate.role}
        </span>
        {dateRange && (
          <span className="text-xs text-zinc-400 dark:text-zinc-500">
            {dateRange}
          </span>
        )}
      </div>
      <div className="mt-2 space-y-1 text-sm text-zinc-700 dark:text-zinc-300">
        {partyLabel && (
          <p>
            Party:{" "}
            <span className="text-zinc-900 dark:text-zinc-100">
              {partyLabel}
            </span>
          </p>
        )}
        {mandate.governing_body_id && (
          <p>
            Governing body: {mandate.governing_body_id}
          </p>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page (server component)                                           */
/* ------------------------------------------------------------------ */

export default async function PoliticianDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [politician, mandatesRes, partiesRes] = await Promise.all([
    fetchPolitician(id),
    fetchPoliticianMandates(id),
    fetchParties(),
  ]);

  if (!politician) {
    notFound();
  }

  const p: Politician = politician;
  const mandates = mandatesRes?.items ?? [];

  const partyNames: Record<string, string> = {};
  for (const party of partiesRes?.items ?? []) {
    partyNames[party.id] = party.abbreviation
      ? `${party.abbreviation} — ${party.name}`
      : party.name;
  }

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 font-sans dark:bg-black">
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6 lg:px-8">
        {/* Breadcrumb */}
        <div className="mb-8">
          <Link
            href="/politicians"
            className="text-sm text-blue-600 hover:underline dark:text-blue-400"
          >
            ← Politicians
          </Link>
        </div>

        {/* Politician header */}
        <section className="mb-10">
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            {p.full_name}
          </h1>
          <div className="mt-3 flex flex-col gap-1">
            <InfoRow label="Given name" value={p.given_name} />
            <InfoRow label="Family name" value={p.family_name} />
            <InfoRow label="Initials" value={p.initials} />
            <InfoRow label="Gender" value={p.gender} />
            <InfoRow label="Date of birth" value={p.date_of_birth} />
          </div>
          {p.aliases.length > 0 && (
            <p className="mt-2 text-sm text-zinc-500 dark:text-zinc-400">
              Also known as: {p.aliases.join(", ")}
            </p>
          )}
        </section>

        {/* Mandates / committee memberships */}
        <section className="mb-10">
          <h2 className="mb-4 text-xl font-semibold text-zinc-800 dark:text-zinc-200">
            Memberships &amp; mandates
          </h2>
          {mandates.length === 0 ? (
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              No mandates recorded for this politician.
            </p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {mandates.map((m) => (
                <MandateCard key={m.id} mandate={m} partyNames={partyNames} />
              ))}
            </div>
          )}
        </section>

        {/* Voting record placeholder */}
        <section>
          <h2 className="mb-4 text-xl font-semibold text-zinc-800 dark:text-zinc-200">
            Voting record
          </h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400">
            Individual voting records will appear here once per-politician vote
            data has been ingested.
          </p>
        </section>
      </main>
    </div>
  );
}
