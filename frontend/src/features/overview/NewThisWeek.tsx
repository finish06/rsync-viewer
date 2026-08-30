import { Link } from "react-router";

import { useMediaNew } from "../../api/hooks";
import { EmptyNote, Skeleton } from "../../components/Panel";
import { dayLabel, localDayKey } from "../../lib/format";

/** Titles shown per day before "+N more" (overview-v2 AC-009). */
const MAX_PER_DAY = 4;
const DAYS = 7;

interface DiaryEntry {
  key: string;
  glyph: string;
  label: string;
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** "S02E05" for one episode, "S02E05–06" for a same-season run, "×N" always. */
function episodeNote(
  episodes: { season: number | null; episode: number | null }[],
): string {
  const numbered = episodes
    .filter((e) => e.season != null && e.episode != null)
    .sort((a, b) => a.season! - b.season! || a.episode! - b.episode!);
  if (numbered.length === 0) return "";
  const first = numbered[0];
  const last = numbered[numbered.length - 1];
  const range =
    numbered.length === 1
      ? `S${pad(first.season!)}E${pad(first.episode!)}`
      : first.season === last.season
        ? `S${pad(first.season!)}E${pad(first.episode!)}–${pad(last.episode!)}`
        : `S${pad(first.season!)}E${pad(first.episode!)}…S${pad(last.season!)}E${pad(last.episode!)}`;
  return range;
}

/** Trailing 7-day watch-list diary (overview-v2 AC-007/008/009). */
export function NewThisWeek() {
  const { data, isPending, isError } = useMediaNew(DAYS);

  if (isPending) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="h-3 w-1/3" />
      </div>
    );
  }
  if (isError || !data)
    return <EmptyNote>Media catalogue unavailable.</EmptyNote>;

  // Bucket arrivals by local day key.
  const byDay = new Map<string, DiaryEntry[]>();
  const push = (iso: string, entry: DiaryEntry) => {
    const key = localDayKey(iso);
    byDay.set(key, [...(byDay.get(key) ?? []), entry]);
  };
  for (const show of data.shows) {
    const perDay = new Map<string, typeof show.new_episodes>();
    for (const ep of show.new_episodes) {
      const key = localDayKey(ep.first_seen_at);
      perDay.set(key, [...(perDay.get(key) ?? []), ep]);
    }
    for (const [key, eps] of perDay) {
      const note = episodeNote(eps);
      push(eps[0].first_seen_at, {
        key: `show-${show.title}-${show.year}-${key}`,
        glyph: "📺",
        label:
          eps.length > 1
            ? `${show.title} ×${eps.length}${note ? ` · ${note}` : ""}`
            : `${show.title}${note ? ` · ${note}` : ""}`,
      });
    }
  }
  for (const movie of data.movies) {
    push(movie.first_seen_at, {
      key: `movie-${movie.title}-${movie.year}`,
      glyph: "🎬",
      label: movie.year ? `${movie.title} (${movie.year})` : movie.title,
    });
  }

  if (byDay.size === 0) return <EmptyNote>Nothing new this week.</EmptyNote>;

  const days = Array.from({ length: DAYS }, (_, i) => {
    const date = new Date(Date.now() - i * 86_400_000);
    const key = localDayKey(date.toISOString());
    return { key, label: dayLabel(key), entries: byDay.get(key) ?? [] };
  });

  return (
    <ol className="space-y-1.5 text-sm" data-testid="new-this-week">
      {days.map((day) => (
        <li
          key={day.key}
          data-testid="media-day"
          data-quiet={day.entries.length === 0}
          className="flex gap-2"
        >
          <span
            className={`w-20 shrink-0 text-xs leading-5 ${
              day.entries.length ? "font-medium" : "text-muted/70"
            }`}
          >
            {day.label}
          </span>
          {day.entries.length === 0 ? (
            <span className="text-xs leading-5 text-muted/70">
              — nothing new
            </span>
          ) : (
            <span className="min-w-0 space-y-0.5">
              {day.entries.slice(0, MAX_PER_DAY).map((entry) => (
                <span
                  key={entry.key}
                  data-testid="media-title"
                  className="flex items-baseline gap-1.5"
                >
                  <span aria-hidden className="text-xs">
                    {entry.glyph}
                  </span>
                  <span className="truncate">{entry.label}</span>
                </span>
              ))}
              {day.entries.length > MAX_PER_DAY && (
                <Link
                  to="/app/media"
                  className="block text-xs text-primary hover:underline"
                >
                  +{day.entries.length - MAX_PER_DAY} more → Media
                </Link>
              )}
            </span>
          )}
        </li>
      ))}
    </ol>
  );
}
