import Link from "next/link";

import { fetchOverviewMetrics } from "@/lib/api";
import type { OverviewMetrics } from "@/lib/types";

/* ------------------------------------------------------------------ */
/*  Stat card — shows a single metric count                           */
/* ------------------------------------------------------------------ */

function StatCard({
  label,
  value,
  href,
}: {
  label: string;
  value: number;
  href?: string;
}) {
  const content = (
    <div className="flex flex-col gap-1 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900">
      <span className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
        {label}
      </span>
      <span className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
        {value.toLocaleString("nl-NL")}
      </span>
    </div>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }
  return content;
}

/* ------------------------------------------------------------------ */
/*  Section card — navigational link to a key section                 */
/* ------------------------------------------------------------------ */

function SectionCard({
  title,
  description,
  href,
}: {
  title: string;
  description: string;
  href: string;
}) {
  return (
    <Link
      href={href}
      className="group flex flex-col gap-2 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md dark:border-zinc-800 dark:bg-zinc-900"
    >
      <h3 className="text-lg font-semibold text-zinc-900 group-hover:text-blue-600 dark:text-zinc-50 dark:group-hover:text-blue-400">
        {title}
      </h3>
      <p className="text-sm text-zinc-500 dark:text-zinc-400">{description}</p>
    </Link>
  );
}

/* ------------------------------------------------------------------ */
/*  Stats grid — renders all metrics or a fallback                    */
/* ------------------------------------------------------------------ */

function StatsGrid({ metrics }: { metrics: OverviewMetrics | null }) {
  if (!metrics) {
    return (
      <p className="text-zinc-500 dark:text-zinc-400">
        Unable to load statistics — the API may be unavailable.
      </p>
    );
  }

  const stats: { label: string; value: number; href?: string }[] = [
    { label: "Meetings", value: metrics.meetings, href: "/meetings" },
    {
      label: "Politicians",
      value: metrics.politicians,
      href: "/politicians",
    },
    { label: "Parties", value: metrics.parties, href: "/parties" },
    { label: "Motions", value: metrics.motions, href: "/motions" },
    { label: "Votes", value: metrics.votes, href: "/votes" },
    { label: "Documents", value: metrics.documents },
    { label: "Amendments", value: metrics.amendments },
    {
      label: "Written questions",
      value: metrics.written_questions,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {stats.map((s) => (
        <StatCard key={s.label} {...s} />
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Dashboard page (server component)                                 */
/* ------------------------------------------------------------------ */

export default async function DashboardPage() {
  const metrics = await fetchOverviewMetrics();

  return (
    <div className="flex flex-1 flex-col bg-zinc-50 font-sans dark:bg-black">
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-12 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-10">
          <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            Curia Dashboard
          </h1>
          <p className="mt-2 text-lg text-zinc-600 dark:text-zinc-400">
            Overview of Dutch political data — meetings, politicians, votes and
            more.
          </p>
        </div>

        {/* Statistics */}
        <section className="mb-12">
          <h2 className="mb-4 text-xl font-semibold text-zinc-800 dark:text-zinc-200">
            Statistics
          </h2>
          <StatsGrid metrics={metrics} />
        </section>

        {/* Navigation cards */}
        <section>
          <h2 className="mb-4 text-xl font-semibold text-zinc-800 dark:text-zinc-200">
            Explore
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <SectionCard
              title="Tweede Kamer"
              description="Browse sessions, debates and votes of the Dutch House of Representatives."
              href="/tweede-kamer"
            />
            <SectionCard
              title="Municipalities"
              description="Explore local council meetings, motions and decisions."
              href="/municipalities"
            />
            <SectionCard
              title="Parties"
              description="View political parties and their representatives."
              href="/parties"
            />
            <SectionCard
              title="Politicians"
              description="Search for politicians and view their activity."
              href="/politicians"
            />
            <SectionCard
              title="Motions"
              description="Track proposed motions and their outcomes."
              href="/motions"
            />
            <SectionCard
              title="Votes"
              description="Examine voting records and results."
              href="/votes"
            />
          </div>
        </section>
      </main>
    </div>
  );
}
