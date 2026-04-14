/** Status badge for meeting lifecycle status. */
export function StatusBadge({ status }: { status: string }) {
  const colours: Record<string, string> = {
    scheduled:
      "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    in_progress:
      "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    completed:
      "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    cancelled:
      "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    postponed:
      "bg-zinc-200 text-zinc-700 dark:bg-zinc-700 dark:text-zinc-300",
  };

  return (
    <span
      className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${colours[status] ?? "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"}`}
    >
      {status.replaceAll("_", " ")}
    </span>
  );
}

/**
 * Type badge — distinguishes national sessions from municipal meetings.
 *
 * Uses keyword matching on the meeting_type field to determine the category.
 */
export function TypeBadge({
  meetingType,
  verbose,
}: {
  meetingType: string | null;
  verbose?: boolean;
}) {
  if (!meetingType) return null;

  const isNational =
    meetingType.toLowerCase().includes("plenary") ||
    meetingType.toLowerCase().includes("national") ||
    meetingType.toLowerCase().includes("chamber") ||
    meetingType.toLowerCase().includes("plenair");

  const label = verbose
    ? isNational
      ? "National session"
      : "Municipal meeting"
    : isNational
      ? "National"
      : "Municipal";

  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
        isNational
          ? "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200"
          : "bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200"
      }`}
    >
      {label}
    </span>
  );
}
