import Link from "next/link";

import { fetchParties, fetchPoliticians } from "@/lib/api";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Politicians — Curia",
  description:
    "Browse Dutch politicians from the Tweede Kamer and municipal councils.",
};

/* ------------------------------------------------------------------ */
/*  Search / filter form (uses query-string navigation)               */
/* ------------------------------------------------------------------ */

function Filters({
  parties,
  currentSearch,
  currentPartyId,
}: {
  parties: { id: string; name: string; abbreviation: string | null }[];
  currentSearch: string;
  currentPartyId: string;
}) {
  return (
    <form method="get" className="mb-8 flex flex-col gap-4 sm:flex-row">
      <input
        type="text"
        name="search"
        defaultValue={currentSearch}
        placeholder="Search by name…"
        className="w-full rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:border-blue-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder-zinc-500 sm:w-64"
      />
      <select
        name="partyId"
        defaultValue={currentPartyId}
        className="w-full rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm text-zinc-900 focus:border-blue-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 sm:w-56"
      >
        <option value="">All parties</option>
        {parties.map((p) => (
          <option key={p.id} value={p.id}>
            {p.abbreviation ? `${p.abbreviation} — ${p.name}` : p.name}
          </option>
        ))}
      </select>
      <button
        type="submit"
        className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
      >
        Filter
      </button>
    </form>
  );
}

/* ------------------------------------------------------------------ */
/*  Pagination controls                                               */
/* ------------------------------------------------------------------ */

function Pagination({
  page,
  pages,
  search,
  partyId,
}: {
  page: number;
  pages: number;
  search: string;
  partyId: string;
}) {
  if (pages <= 1) return null;

  function href(p: number) {
    const qs = new URLSearchParams();
    qs.set("page", String(p));
    if (search) qs.set("search", search);
    if (partyId) qs.set("partyId", partyId);
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
/*  Page (server component)                                           */
/* ------------------------------------------------------------------ */

export default async function PoliticiansPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const search = typeof params.search === "string" ? params.search : "";
  const partyId = typeof params.partyId === "string" ? params.partyId : "";
  const page = Math.max(1, Number(params.page) || 1);

  const [politiciansRes, partiesRes] = await Promise.all([
    fetchPoliticians({ page, search: search || undefined, partyId: partyId || undefined }),
    fetchParties(),
  ]);

  const parties = (partiesRes?.items ?? []).map((p) => ({
    id: p.id,
    name: p.name,
    abbreviation: p.abbreviation,
  }));

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
            Politicians
          </h1>
          <p className="mt-1 text-zinc-600 dark:text-zinc-400">
            Browse Tweede Kamer members and municipal council members.
          </p>
        </div>

        {/* Filters */}
        <Filters
          parties={parties}
          currentSearch={search}
          currentPartyId={partyId}
        />

        {/* Results */}
        {!politiciansRes ? (
          <p className="text-zinc-500 dark:text-zinc-400">
            Unable to load politicians — the API may be unavailable.
          </p>
        ) : politiciansRes.items.length === 0 ? (
          <p className="text-zinc-500 dark:text-zinc-400">
            No politicians found matching your criteria.
          </p>
        ) : (
          <>
            <p className="mb-4 text-sm text-zinc-500 dark:text-zinc-400">
              {politiciansRes.total.toLocaleString("nl-NL")} result
              {politiciansRes.total !== 1 ? "s" : ""}
            </p>
            <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {politiciansRes.items.map((p) => (
                <li key={p.id}>
                  <Link
                    href={`/politicians/${p.id}`}
                    className="group flex flex-col gap-1 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900"
                  >
                    <span className="text-lg font-semibold text-zinc-900 group-hover:text-blue-600 dark:text-zinc-50 dark:group-hover:text-blue-400">
                      {p.full_name}
                    </span>
                    {p.initials && (
                      <span className="text-sm text-zinc-500 dark:text-zinc-400">
                        {p.initials}
                      </span>
                    )}
                    {p.date_of_birth && (
                      <span className="text-xs text-zinc-400 dark:text-zinc-500">
                        Born {p.date_of_birth}
                      </span>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
            <Pagination
              page={politiciansRes.page}
              pages={politiciansRes.pages}
              search={search}
              partyId={partyId}
            />
          </>
        )}
      </main>
    </div>
  );
}
