"""Seed the database with realistic dev data.

Run via: docker-compose exec app python -m scripts.seed
Or automatically via docker-compose.seed.yml entrypoint.
"""

import random
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlmodel import SQLModel, Session, select

from app.database import engine

# Import all models so SQLModel.metadata knows about them
import app.models.sync_log  # noqa: F401
import app.models.webhook  # noqa: F401
import app.models.webhook_options  # noqa: F401
import app.models.failure_event  # noqa: F401
import app.models.notification_log  # noqa: F401
from app.models.failure_event import FailureEvent
from app.models.notification_log import NotificationLog
from app.models.sync_log import SyncLog
from app.models.webhook import WebhookEndpoint
from app.models.webhook_options import WebhookOptions

# Fixed UUIDs for cross-referencing
WH_DISCORD_ID = UUID("a1b2c3d4-0001-4000-8000-000000000001")
WH_HA_ID = UUID("a1b2c3d4-0002-4000-8000-000000000002")

FAIL_IDS = [UUID(f"f1000000-000{i}-4000-8000-000000000001") for i in range(1, 6)]
FE_IDS = [UUID(f"fe000000-000{i}-4000-8000-000000000001") for i in range(1, 6)]


def make_raw_output(
    *,
    source: str,
    files: list[str],
    file_count: int,
    dir_count: int,
    total_size: int,
    transferred: int,
    bytes_recv: int,
    speed: int,
    speedup: float,
    is_dry_run: bool = False,
    error_lines: str = "",
) -> str:
    """Generate realistic rsync raw output."""
    lines = ["sending incremental file list"]
    lines.extend(files)
    if error_lines:
        lines.append(error_lines)
    lines.append("")
    lines.append(
        f"Number of files: {file_count} (reg: {file_count - dir_count}, dir: {dir_count})"
    )
    lines.append("Number of created files: 2")
    lines.append("Number of deleted files: 0")
    lines.append(f"Total file size: {total_size:,} bytes")
    lines.append(f"Total transferred file size: {transferred:,} bytes")
    if is_dry_run:
        lines.append("Literal data: 0 bytes")
    else:
        lines.append(f"Literal data: {transferred:,} bytes")
    lines.append("Matched data: 0 bytes")
    lines.append("File list size: 1,234")
    lines.append(f"Total bytes sent: {transferred:,}")
    lines.append(f"Total bytes received: {bytes_recv:,}")
    lines.append("")
    lines.append(
        f"sent {transferred:,} bytes  received {bytes_recv:,} bytes  {speed:,} bytes/sec"
    )
    dry_suffix = " (DRY RUN)" if is_dry_run else ""
    lines.append(f"total size is {total_size:,}  speedup is {speedup:.2f}{dry_suffix}")
    return "\n".join(lines) + "\n"


def seed_database() -> None:
    """Insert seed data if the database is empty."""
    # Create tables if they don't exist
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # Check if data already exists
        existing = session.exec(select(SyncLog).limit(1)).first()
        if existing:
            print("Database already has data, skipping seed.")
            return

        now = datetime.now(timezone.utc)
        base = now - timedelta(days=30)
        random.seed(42)  # Reproducible data

        # ==================================================================
        # Webhooks
        # ==================================================================
        discord_wh = WebhookEndpoint(
            id=WH_DISCORD_ID,
            name="Discord Alerts",
            url="https://discord.com/api/webhooks/1234567890/abcdefghijklmnop",
            webhook_type="discord",
            enabled=True,
            created_at=base,
            updated_at=base,
        )
        ha_wh = WebhookEndpoint(
            id=WH_HA_ID,
            name="Home Assistant",
            url="http://homeassistant.local:8123/api/webhook/rsync-alerts",
            headers={"Authorization": "Bearer LONG_LIVED_TOKEN"},
            webhook_type="generic",
            enabled=True,
            created_at=base,
            updated_at=base,
        )
        session.add(discord_wh)
        session.add(ha_wh)

        session.add(
            WebhookOptions(
                webhook_endpoint_id=WH_DISCORD_ID,
                options={"username": "Rsync Bot"},
                created_at=base,
                updated_at=base,
            )
        )
        session.add(
            WebhookOptions(
                webhook_endpoint_id=WH_HA_ID,
                options={},
                created_at=base,
                updated_at=base,
            )
        )

        # ==================================================================
        # Successful sync logs
        # ==================================================================
        sync_logs: list[SyncLog] = []

        # Photos — ~18 entries, roughly daily
        for i in range(18):
            log_date = base + timedelta(days=i * 1.6, hours=14 + random.random() * 2)
            dur = 120 + random.randint(0, 600)
            fcount = 50 + random.randint(0, 500)
            tsize = 100_000_000 + random.randint(0, 900_000_000)
            bsent = int(tsize * (0.01 + random.random() * 0.15))
            brecv = 1024 + random.randint(0, 10240)
            speed = bsent // max(dur, 1)
            speedup = tsize / max(bsent, 1)
            is_dry = i in (2, 10)

            files = [
                f"Photos/2026/IMG_{1000 + i}.jpg",
                f"Photos/2026/IMG_{1001 + i}.jpg",
            ]
            raw = make_raw_output(
                source="photos",
                files=files,
                file_count=fcount,
                dir_count=5,
                total_size=tsize,
                transferred=bsent,
                bytes_recv=brecv,
                speed=speed,
                speedup=speedup,
                is_dry_run=is_dry,
            )

            log = SyncLog(
                source_name="photos",
                start_time=log_date,
                end_time=log_date + timedelta(seconds=dur),
                raw_content=raw,
                total_size_bytes=tsize,
                bytes_sent=bsent,
                bytes_received=brecv,
                transfer_speed=float(speed),
                speedup_ratio=speedup,
                file_count=fcount,
                file_list=files,
                exit_code=0,
                status="completed",
                is_dry_run=is_dry,
                created_at=log_date,
            )
            sync_logs.append(log)
            session.add(log)

        # Videos — ~14 entries, every ~2 days
        for i in range(14):
            log_date = base + timedelta(days=i * 2.1, hours=3 + random.random())
            dur = 300 + random.randint(0, 1800)
            fcount = 10 + random.randint(0, 50)
            tsize = 1_000_000_000 + random.randint(0, 4_000_000_000)
            bsent = int(tsize * (0.02 + random.random() * 0.20))
            brecv = 2048 + random.randint(0, 20480)
            speed = bsent // max(dur, 1)
            speedup = tsize / max(bsent, 1)

            files = [f"Videos/Movies/movie_{100 + i}.mkv"]
            raw = make_raw_output(
                source="videos",
                files=files,
                file_count=fcount,
                dir_count=2,
                total_size=tsize,
                transferred=bsent,
                bytes_recv=brecv,
                speed=speed,
                speedup=speedup,
            )

            log = SyncLog(
                source_name="videos",
                start_time=log_date,
                end_time=log_date + timedelta(seconds=dur),
                raw_content=raw,
                total_size_bytes=tsize,
                bytes_sent=bsent,
                bytes_received=brecv,
                transfer_speed=float(speed),
                speedup_ratio=speedup,
                file_count=fcount,
                file_list=files,
                exit_code=0,
                status="completed",
                is_dry_run=False,
                created_at=log_date,
            )
            sync_logs.append(log)
            session.add(log)

        # Files — ~13 entries, every ~2 days
        for i in range(13):
            log_date = base + timedelta(days=i * 2.3, hours=6 + random.random() * 3)
            dur = 30 + random.randint(0, 120)
            fcount = 200 + random.randint(0, 2000)
            tsize = 10_000_000 + random.randint(0, 200_000_000)
            bsent = int(tsize * (0.005 + random.random() * 0.05))
            brecv = 512 + random.randint(0, 4096)
            speed = bsent // max(dur, 1)
            speedup = tsize / max(bsent, 1)
            is_dry = i == 5

            files = ["Documents/notes.txt", "Documents/budget.xlsx"]
            raw = make_raw_output(
                source="files",
                files=files,
                file_count=fcount,
                dir_count=20,
                total_size=tsize,
                transferred=bsent,
                bytes_recv=brecv,
                speed=speed,
                speedup=speedup,
                is_dry_run=is_dry,
            )

            log = SyncLog(
                source_name="files",
                start_time=log_date,
                end_time=log_date + timedelta(seconds=dur),
                raw_content=raw,
                total_size_bytes=tsize,
                bytes_sent=bsent,
                bytes_received=brecv,
                transfer_speed=float(speed),
                speedup_ratio=speedup,
                file_count=fcount,
                file_list=files,
                exit_code=0,
                status="completed",
                is_dry_run=is_dry,
                created_at=log_date,
            )
            sync_logs.append(log)
            session.add(log)

        # ==================================================================
        # Failed sync logs (5)
        # ==================================================================
        failures_data = [
            {
                "id": FAIL_IDS[0],
                "source": "photos",
                "offset_days": 5,
                "exit_code": 23,
                "dur": 45,
                "error": "rsync: [sender] write error: Broken pipe (32)\nrsync error: some files/attrs were not transferred (code 23) at main.c(1338)",
                "detail": "Exit code 23: partial transfer",
                "tsize": 524_288_000,
                "bsent": 6_789_012,
            },
            {
                "id": FAIL_IDS[1],
                "source": "videos",
                "offset_days": 10,
                "exit_code": 11,
                "dur": 180,
                "error": 'rsync: write failed on "/backup/Videos/Movies/big_movie.mkv": No space left on device (28)\nrsync error: error in file IO (code 11) at receiver.c(393)',
                "detail": "Exit code 11: no space left on device",
                "tsize": 8_589_934_592,
                "bsent": 2_147_483_648,
            },
            {
                "id": FAIL_IDS[2],
                "source": "files",
                "offset_days": 15,
                "exit_code": 23,
                "dur": 15,
                "error": 'rsync: send_files failed to open "/home/user/Documents/private/secrets.txt": Permission denied (13)\nrsync error: some files/attrs were not transferred (code 23) at main.c(1338)',
                "detail": "Exit code 23: permission denied",
                "tsize": 104_857_600,
                "bsent": 523_456,
            },
            {
                "id": FAIL_IDS[3],
                "source": "photos",
                "offset_days": 22,
                "exit_code": 10,
                "dur": 5,
                "error": "rsync: failed to connect to nas.local (192.168.1.100): Connection refused (111)\nrsync error: error in socket IO (code 10) at clientserver.c(139)",
                "detail": "Exit code 10: connection refused",
                "tsize": None,
                "bsent": None,
            },
            {
                "id": FAIL_IDS[4],
                "source": "videos",
                "offset_days": 27,
                "exit_code": 30,
                "dur": 300,
                "error": "[sender] io timeout after 300 seconds -- exiting\nrsync error: timeout in data send/receive (code 30) at io.c(204)",
                "detail": "Exit code 30: timeout",
                "tsize": 4_294_967_296,
                "bsent": 536_870_912,
            },
        ]

        failed_logs = []
        for fd in failures_data:
            log_date = base + timedelta(days=fd["offset_days"], hours=8)

            if fd["tsize"] is not None:
                brecv = random.randint(1024, 8192)
                speed = fd["bsent"] // max(fd["dur"], 1)
                speedup = fd["tsize"] / max(fd["bsent"], 1)
                raw = make_raw_output(
                    source=fd["source"],
                    files=[f"failed_file_{fd['exit_code']}"],
                    file_count=random.randint(10, 500),
                    dir_count=5,
                    total_size=fd["tsize"],
                    transferred=fd["bsent"],
                    bytes_recv=brecv,
                    speed=speed,
                    speedup=speedup,
                    error_lines=fd["error"],
                )
            else:
                raw = fd["error"] + "\n"
                brecv = None
                speed = None
                speedup = None

            log = SyncLog(
                id=fd["id"],
                source_name=fd["source"],
                start_time=log_date,
                end_time=log_date + timedelta(seconds=fd["dur"]),
                raw_content=raw,
                total_size_bytes=fd["tsize"],
                bytes_sent=fd["bsent"],
                bytes_received=brecv,
                transfer_speed=float(speed) if speed else None,
                speedup_ratio=speedup,
                file_count=None if fd["tsize"] is None else random.randint(10, 500),
                exit_code=fd["exit_code"],
                status="failed",
                is_dry_run=False,
                created_at=log_date,
            )
            failed_logs.append(log)
            session.add(log)

        # Flush so sync_log IDs exist for foreign keys
        session.flush()

        # ==================================================================
        # Failure events
        # ==================================================================
        failure_events = []
        for i, fd in enumerate(failures_data):
            log_date = base + timedelta(days=fd["offset_days"], hours=8)
            fe = FailureEvent(
                id=FE_IDS[i],
                source_name=fd["source"],
                failure_type="exit_code",
                detected_at=log_date,
                sync_log_id=fd["id"],
                notified=True,
                details=fd["detail"],
                created_at=log_date,
            )
            failure_events.append(fe)
            session.add(fe)

        # ==================================================================
        # Notification logs
        # ==================================================================
        for i, fe in enumerate(failure_events):
            notif_time = fe.detected_at + timedelta(minutes=1)
            # Discord notification — always succeeds
            session.add(
                NotificationLog(
                    failure_event_id=fe.id,
                    webhook_endpoint_id=WH_DISCORD_ID,
                    status="success",
                    http_status_code=204,
                    attempt_number=1,
                    created_at=notif_time,
                )
            )
            # HA notification — one failure for variety
            if i == 2:
                session.add(
                    NotificationLog(
                        failure_event_id=fe.id,
                        webhook_endpoint_id=WH_HA_ID,
                        status="failed",
                        error_message="Connection refused",
                        attempt_number=1,
                        created_at=notif_time,
                    )
                )
            else:
                session.add(
                    NotificationLog(
                        failure_event_id=fe.id,
                        webhook_endpoint_id=WH_HA_ID,
                        status="success",
                        http_status_code=200,
                        attempt_number=1,
                        created_at=notif_time,
                    )
                )

        session.commit()

        # Summary
        total_logs = 18 + 14 + 13 + 5
        print(f"Seeded {total_logs} sync logs (3 dry runs, 5 failures)")
        print("Seeded 2 webhook endpoints (Discord + Home Assistant)")
        print("Seeded 5 failure events with 10 notification logs")
        print("Done!")


if __name__ == "__main__":
    seed_database()
