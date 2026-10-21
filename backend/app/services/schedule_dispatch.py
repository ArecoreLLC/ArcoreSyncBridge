"""Dispatch persisted sync schedules from a short, periodic Celery Beat task."""
import logging
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.core import CeleryPeriodicTask, SyncDefinition
from app.services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)


def dispatch_due_schedules(db: Session, enqueue, *, now: datetime | None = None) -> int:
    """Publish due jobs while holding row locks; failed publishes remain due.

    Delivery is at least once: a crash after broker publish but before DB commit
    can redeliver a job. Run only one Beat process, as with standard Celery Beat.
    """
    now = now or datetime.now(UTC)
    eligible = (
        SyncDefinition.schedule_enabled.is_(True),
        SyncDefinition.is_paused.is_(False),
        CeleryPeriodicTask.enabled.is_(True),
        or_(SyncDefinition.next_scheduled_run <= now, SyncDefinition.next_scheduled_run.is_(None)),
    )
    ids = db.execute(
        select(SyncDefinition.id)
        .join(CeleryPeriodicTask, CeleryPeriodicTask.sync_def_id == SyncDefinition.id)
        .where(*eligible)
        .order_by(SyncDefinition.next_scheduled_run, SyncDefinition.id)
        .limit(100)
    ).scalars().all()
    db.commit()
    dispatched = 0
    for sync_def_id in ids:
        try:
            row = db.execute(
                select(SyncDefinition, CeleryPeriodicTask)
                .join(CeleryPeriodicTask, CeleryPeriodicTask.sync_def_id == SyncDefinition.id)
                .where(SyncDefinition.id == sync_def_id, *eligible)
                .with_for_update(skip_locked=True)
            ).first()
            if row is None:
                db.rollback()
                continue
            sync_def, task = row
            next_run = ScheduleService.preview_schedule(
                sync_def.schedule_type,
                sync_def.schedule_interval_seconds,
                sync_def.schedule_cron_expression,
                sync_def.schedule_timezone,
                count=1,
                now=now,
            )[0]
            # Legacy records without a due time are initialized without firing.
            if sync_def.next_scheduled_run is not None:
                enqueue(str(sync_def.id))
                task.last_run_at = now
                task.total_run_count += 1
            published = sync_def.next_scheduled_run is not None
            sync_def.next_scheduled_run = next_run
            db.commit()
            dispatched += int(published)
        except Exception:
            db.rollback()
            logger.exception("Failed to dispatch schedule %s", sync_def_id)
    return dispatched
