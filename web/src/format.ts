const ACRONYMS = new Set(["mri", "ct", "mra", "pet", "us", "ekg", "eeg"]);

/** "lumbar-mri" -> "Lumbar MRI", "sample-policy" -> "Sample Policy" */
export function humanizePolicy(policyId: string): string {
  return policyId
    .split(/[-_]/)
    .map((word) =>
      ACRONYMS.has(word.toLowerCase())
        ? word.toUpperCase()
        : word.charAt(0).toUpperCase() + word.slice(1),
    )
    .join(" ");
}

/** A short, human-friendly case tag from the full UUID. */
export function shortId(uuid: string): string {
  return `case-${uuid.replace(/-/g, "").slice(0, 4)}`;
}

/** Today -> "9:14a"; otherwise the short weekday. */
export function formatTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const now = new Date();
  if (date.toDateString() === now.toDateString()) {
    const minutes = String(date.getMinutes()).padStart(2, "0");
    const meridiem = date.getHours() < 12 ? "a" : "p";
    const hour = date.getHours() % 12 || 12;
    return `${hour}:${minutes}${meridiem}`;
  }
  return date.toLocaleDateString(undefined, { weekday: "short" });
}
