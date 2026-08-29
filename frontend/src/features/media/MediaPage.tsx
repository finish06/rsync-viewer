import { useMemo } from "react";
import { Link, useSearchParams } from "react-router";

import { useMediaNew } from "../../api/hooks";
import type { EpisodeRead, MovieRead } from "../../api/types";
import { EmptyNote, ErrorCard, Panel, Skeleton } from "../../components/Panel";
import { episodeLabel, formatRelative, localDayKey } from "../../lib/format";

const WINDOWS = [7, 14, 30, 90];

/** Link to the Transfers page filtered to the day and source of first sighting. */
export function transferLink(item: {
  first_seen_at: string;
  source_name: string;
}): string {
  const day = localDayKey(item.first_seen_at);
  const params = new URLSearchParams({
    range: "custom",
    from: day,
    to: day,
    source: item.source_name,
  });
  return `/app/transfers?${params.toString()}`;
}

export function MediaPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const days = useMemo(() => {
    const raw = Number(searchParams.get("days"));
    return WINDOWS.includes(raw) ? raw : 7;
  }, [searchParams]);
  const media = useMediaNew(days);

  const episodes =
    media.data?.shows.reduce((n, s) => n + s.new_episodes.length, 0) ?? 0;

  return (
    <div className="space-y-4">
      <div
        className="card flex flex-wrap items-center gap-3 p-3 text-sm"
        data-testid="media-filters"
      >
        <label className="flex items-center gap-1">
          <span className="text-muted">New in the last</span>
          <select
            aria-label="Window"
            value={days}
            onChange={(e) =>
              setSearchParams(
                e.target.value === "7" ? {} : { days: e.target.value },
                { replace: true },
              )
            }
            className="rounded border border-border bg-card px-2 py-1"
          >
            {WINDOWS.map((w) => (
              <option key={w} value={w}>
                {w} days
              </option>
            ))}
          </select>
        </label>
        {media.isSuccess && (
          <span className="ml-auto text-muted" data-testid="media-counts">
            🎬 <b className="text-text">{media.data.movies.length}</b>{" "}
            {media.data.movies.length === 1 ? "movie" : "movies"} · 📺{" "}
            <b className="text-text">{media.data.shows.length}</b>{" "}
            {media.data.shows.length === 1 ? "show" : "shows"} ·{" "}
            <b className="text-text">{episodes}</b>{" "}
            {episodes === 1 ? "episode" : "episodes"}
          </span>
        )}
      </div>

      {media.isError && (
        <ErrorCard
          message="Could not load the media catalogue."
          onRetry={() => void media.refetch()}
        />
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Shows" testId="shows-panel">
          {media.isPending && <Skeleton className="h-24" />}
          {media.isSuccess && media.data.shows.length === 0 && (
            <EmptyNote>No new episodes in this window.</EmptyNote>
          )}
          {media.isSuccess && media.data.shows.length > 0 && (
            <ul className="divide-y divide-border">
              {media.data.shows.map((show) => (
                <li
                  key={`${show.title}-${show.year}`}
                  data-testid="show-item"
                  className="py-2"
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="font-medium">
                      {show.title}
                      {show.year && (
                        <span className="text-muted"> ({show.year})</span>
                      )}
                    </span>
                    <span className="text-xs text-muted">
                      {show.new_episodes.length} new
                    </span>
                  </div>
                  <ul className="mt-1 flex flex-wrap gap-1.5">
                    {show.new_episodes.map((ep) => (
                      <li key={`${ep.season}-${ep.episode}`}>
                        <EpisodeChip episode={ep} />
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Movies" testId="movies-panel">
          {media.isPending && <Skeleton className="h-24" />}
          {media.isSuccess && media.data.movies.length === 0 && (
            <EmptyNote>No new movies in this window.</EmptyNote>
          )}
          {media.isSuccess && media.data.movies.length > 0 && (
            <ul className="divide-y divide-border">
              {media.data.movies.map((movie) => (
                <MovieRow key={`${movie.title}-${movie.year}`} movie={movie} />
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}

function EpisodeChip({ episode }: { episode: EpisodeRead }) {
  return (
    <Link
      to={transferLink(episode)}
      title={`First seen ${formatRelative(episode.first_seen_at)} from ${episode.source_name}`}
      className="inline-block rounded border border-border px-1.5 py-0.5 font-mono text-xs hover:border-primary"
    >
      {episodeLabel(episode.season, episode.episode)}
    </Link>
  );
}

function MovieRow({ movie }: { movie: MovieRead }) {
  return (
    <li
      data-testid="movie-item"
      className="flex items-baseline justify-between gap-2 py-2"
    >
      <span className="font-medium">
        {movie.title}
        {movie.year && <span className="text-muted"> ({movie.year})</span>}
      </span>
      <Link
        to={transferLink(movie)}
        className="text-xs text-muted hover:text-primary"
      >
        {formatRelative(movie.first_seen_at)} · {movie.source_name} ▸
      </Link>
    </li>
  );
}
