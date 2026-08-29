import { Link } from "react-router";

import { useMediaNew } from "../../api/hooks";
import { EmptyNote, Skeleton } from "../../components/Panel";
import { episodeLabel } from "../../lib/format";

const MAX_TITLES = 5;

export function NewThisWeek() {
  const { data, isPending, isError } = useMediaNew(7);

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

  const episodes = data.shows.reduce((n, s) => n + s.new_episodes.length, 0);
  const titles = [
    ...data.shows.map((s) => ({
      key: `show-${s.title}-${s.year}`,
      label: s.title,
      note:
        s.new_episodes.length === 1
          ? episodeLabel(s.new_episodes[0].season, s.new_episodes[0].episode)
          : `${s.new_episodes.length} episodes`,
      glyph: "📺",
    })),
    ...data.movies.map((m) => ({
      key: `movie-${m.title}-${m.year}`,
      label: m.year ? `${m.title} (${m.year})` : m.title,
      note: "",
      glyph: "🎬",
    })),
  ];

  if (titles.length === 0) return <EmptyNote>Nothing new this week.</EmptyNote>;

  return (
    <div data-testid="new-this-week">
      <p className="mb-2 text-sm">
        <span className="font-semibold">🎬 {data.movies.length}</span>{" "}
        <span className="text-muted">
          {data.movies.length === 1 ? "movie" : "movies"}
        </span>
        <span className="mx-2 text-muted">·</span>
        <span className="font-semibold">📺 {data.shows.length}</span>{" "}
        <span className="text-muted">
          {data.shows.length === 1 ? "show" : "shows"} · {episodes}{" "}
          {episodes === 1 ? "episode" : "episodes"}
        </span>
      </p>
      <ul className="space-y-1 text-sm">
        {titles.slice(0, MAX_TITLES).map((t) => (
          <li key={t.key} className="flex items-baseline gap-2">
            <span aria-hidden>{t.glyph}</span>
            <span className="truncate">{t.label}</span>
            {t.note && <span className="text-xs text-muted">{t.note}</span>}
          </li>
        ))}
      </ul>
      <Link
        to="/app/media"
        className="mt-2 inline-block text-sm text-primary hover:underline"
      >
        {titles.length > MAX_TITLES
          ? `+${titles.length - MAX_TITLES} more → Media`
          : "→ Media"}
      </Link>
    </div>
  );
}
