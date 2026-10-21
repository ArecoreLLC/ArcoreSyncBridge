from uuid import UUID
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from croniter import croniter

from app.core.time import utc_now
from app.models.core import SyncDefinition, CeleryPeriodicTask


class ScheduleService:
    def __init__(self, db: Session):
        self.db = db

    def enable_schedule(
        self,
        sync_def_id: UUID,
        schedule_type: str,  # "INTERVAL" or "CRON"
        interval_seconds: Optional[int] = None,
        cron_expression: Optional[str] = None,
        timezone: str = "UTC"
    ):
        """
        Enable scheduled sync for a sync definition.
        Creates or updates CeleryPeriodicTask.
        """
        sync_def = self.db.get(SyncDefinition, sync_def_id, with_for_update=True)
        if not sync_def:
            raise ValueError("Sync definition not found")

        # Calculate and validate before changing any persistent objects.
        next_run = self.preview_schedule(
            schedule_type, interval_seconds, cron_expression, timezone, count=1
        )[0]
        if schedule_type == "INTERVAL":
            cron_expression = None
        else:
            interval_seconds = None

        # Update SyncDefinition
        sync_def.schedule_enabled = True
        sync_def.schedule_type = schedule_type
        sync_def.schedule_interval_seconds = interval_seconds
        sync_def.schedule_cron_expression = cron_expression
        sync_def.schedule_timezone = timezone
        sync_def.next_scheduled_run = next_run

        # Create or update CeleryPeriodicTask
        task_name = f"sync_def_{sync_def_id}_scheduled"
        stmt = select(CeleryPeriodicTask).where(CeleryPeriodicTask.name == task_name)
        periodic_task = self.db.execute(stmt).scalar_one_or_none()

        if not periodic_task:
            periodic_task = CeleryPeriodicTask(
                name=task_name,
                task="app.worker.tasks.run_scheduled_sync",
                sync_def_id=sync_def_id,
                args=[str(sync_def_id)],
                kwargs={},
                enabled=True
            )
            self.db.add(periodic_task)
        else:
            periodic_task.enabled = True
            periodic_task.sync_def_id = sync_def_id
            periodic_task.args = [str(sync_def_id)]

        # Set schedule based on type
        if schedule_type == "INTERVAL":
            periodic_task.interval_seconds = interval_seconds
            # Clear crontab fields
            periodic_task.crontab_minute = None
            periodic_task.crontab_hour = None
            periodic_task.crontab_day_of_week = None
            periodic_task.crontab_day_of_month = None
            periodic_task.crontab_month_of_year = None
        else:  # CRON
            # Parse cron expression (format: "minute hour day month day_of_week")
            parts = cron_expression.split()
            if len(parts) != 5:
                raise ValueError("Cron must have 5 parts: minute hour day month day_of_week")

            periodic_task.crontab_minute = parts[0]
            periodic_task.crontab_hour = parts[1]
            periodic_task.crontab_day_of_month = parts[2]
            periodic_task.crontab_month_of_year = parts[3]
            periodic_task.crontab_day_of_week = parts[4]
            periodic_task.interval_seconds = None

        periodic_task.date_changed = utc_now()

        self.db.commit()
        return {"message": "Schedule enabled", "next_run": next_run}

    def disable_schedule(self, sync_def_id: UUID):
        """Disable scheduled sync."""
        sync_def = self.db.get(SyncDefinition, sync_def_id, with_for_update=True)
        if not sync_def:
            raise ValueError("Sync definition not found")

        sync_def.schedule_enabled = False
        sync_def.next_scheduled_run = None

        # Disable periodic task
        task_name = f"sync_def_{sync_def_id}_scheduled"
        stmt = select(CeleryPeriodicTask).where(CeleryPeriodicTask.name == task_name)
        periodic_task = self.db.execute(stmt).scalar_one_or_none()

        if periodic_task:
            periodic_task.enabled = False
            periodic_task.date_changed = utc_now()

        self.db.commit()
        return {"message": "Schedule disabled"}

    def delete_schedule(self, sync_def_id: UUID):
        """Completely remove schedule."""
        sync_def = self.db.get(SyncDefinition, sync_def_id, with_for_update=True)
        if not sync_def:
            raise ValueError("Sync definition not found")
        sync_def.schedule_enabled = False
        sync_def.next_scheduled_run = None
        sync_def.schedule_type = None
        sync_def.schedule_interval_seconds = None
        sync_def.schedule_cron_expression = None
        sync_def.schedule_timezone = "UTC"

        task_name = f"sync_def_{sync_def_id}_scheduled"
        stmt = delete(CeleryPeriodicTask).where(CeleryPeriodicTask.name == task_name)
        self.db.execute(stmt)
        self.db.commit()
        return {"message": "Schedule deleted"}

    @staticmethod
    def preview_schedule(
        schedule_type: str,
        interval_seconds: Optional[int] = None,
        cron_expression: Optional[str] = None,
        timezone: str = "UTC",
        *,
        count: int = 5,
        now: Optional[datetime] = None,
    ) -> list[datetime]:
        """Validate a schedule and return upcoming timezone-aware UTC instants."""
        if not 1 <= count <= 10:
            raise ValueError("Preview count must be between 1 and 10")
        try:
            zone = ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Invalid timezone: {timezone}") from exc
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        now = now.astimezone(UTC)
        if schedule_type == "INTERVAL":
            if not interval_seconds or not 60 <= interval_seconds <= 2_147_483_647:
                raise ValueError("Interval must be between 60 and 2147483647 seconds")
            try:
                return [now + timedelta(seconds=interval_seconds * i) for i in range(1, count + 1)]
            except OverflowError as exc:
                raise ValueError("Interval is too large") from exc
        if schedule_type != "CRON":
            raise ValueError("schedule_type must be INTERVAL or CRON")
        if not cron_expression or len(cron_expression.split()) != 5:
            raise ValueError("Cron must have 5 parts: minute hour day month day_of_week")
        try:
            iterator = croniter(cron_expression, now.astimezone(zone))
            return [iterator.get_next(datetime).astimezone(UTC) for _ in range(count)]
        except (ValueError, KeyError, OverflowError) as exc:
            raise ValueError(f"Invalid cron expression: {exc}") from exc

    def _calculate_next_run(
        self,
        schedule_type: str,
        interval_seconds: Optional[int],
        cron_expression: Optional[str],
        timezone: str,
    ) -> datetime:
        return self.preview_schedule(
            schedule_type, interval_seconds, cron_expression, timezone, count=1
        )[0]
