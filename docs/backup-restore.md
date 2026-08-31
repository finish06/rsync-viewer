# Backup & restore runbook

Spec: `specs/backup-restore.md`. Archives are `pg_dump` custom-format files —
compressed, and restorable table-by-table if ever needed.

## Take a backup

Inside the app container (images from v2.22.0 ship the postgres client
tools and the `scripts/` package; `DATABASE_URL` is already set):

```bash
docker compose exec app python -m scripts.backup --dir /data/backups --keep 14
```

Mount a host directory for `/data/backups` in your compose file so archives
survive the container:

```yaml
  app:
    volumes:
      - ./backups:/data/backups
```

From the host instead (needs `pg_dump` ≥ your server version):

```bash
DATABASE_URL=postgresql://postgres:…@localhost:5432/rsync_viewer \
  python -m scripts.backup --dir ./backups --keep 14
```

## Schedule it

Host crontab — daily at 03:15, keeping two weeks:

```cron
15 3 * * * cd /path/to/rsync-viewer && docker compose exec -T app python -m scripts.backup --dir /data/backups --keep 14 >> backups/backup.log 2>&1
```

## Restore (full recovery)

1. Stop the app so nothing writes: `docker compose stop app`
2. Restore over the existing database (**this replaces all data**):

   ```bash
   docker compose exec -T db bash -lc 'true'   # ensure db is up
   docker compose run --rm app python -m scripts.restore /data/backups/rsync-viewer-YYYYMMDD-HHMMSS.dump --yes
   ```

3. Start the app: `docker compose start app`. Migrations run automatically;
   restoring an older archive onto newer code is safe (alembic upgrades it).

## Verify a backup without touching production

Restore into a scratch database and compare counts:

```bash
docker compose exec -T db createdb -U postgres scratch_verify
DATABASE_URL=postgresql://postgres:…@localhost:5432/scratch_verify \
  python -m scripts.restore backups/<archive>.dump --yes
# spot-check: row counts for sync_logs, users, media_items match expectations
docker compose exec -T db dropdb -U postgres scratch_verify
```

`pg_restore --list backups/<archive>.dump` is a fast integrity check.

Note: restoring into a **fresh** scratch database may exit non-zero with
"… does not exist" warnings from `--clean` — the data still restores;
verify with the row counts above. Restoring over the real database (the
recovery path) completes cleanly.

## Notes

- Rotation only ever deletes files matching `rsync-viewer-*.dump`; manual
  copies with other names are never touched.
- A failed dump exits non-zero and leaves no partial file.
- Credentials are read from `DATABASE_URL` and never printed.
