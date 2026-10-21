import os
from uuid import UUID
from datetime import datetime
from celery import Task
from celery.utils.log import get_task_logger
import redis

from app.worker.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.core import SyncDefinition
from app.services.pusher import Pusher
from app.services.synchronizer import Synchronizer
from app.services.run_history import RunHistoryService
from app.services.reconciliation import ReconciliationService

logger = get_task_logger(__name__)

# Redis client for distributed locks
redis_client = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))


class SingletonTask(Task):
    """
    Task that prevents concurrent execution of the same sync definition.
    Uses Redis lock with sync_def_id as key.
    """
    def apply_async(self, args=None, kwargs=None, **options):
        # Get sync_def_id from args or kwargs
        sync_def_id = args[0] if args else (kwargs or {}).get('sync_def_id')
        lock_key = f"sync_lock:{sync_def_id}"

        # Try to acquire lock (non-blocking check)
        lock = redis_client.lock(lock_key, timeout=3600, blocking=False)  # 1 hour max
        if not lock.acquire(blocking=False):
            logger.warning(f"Sync {sync_def_id} already running, skipping scheduled execution")
            # Log to audit table
            from app.services.schedule_audit import ScheduleAuditService
            db = SessionLocal()
            try:
                audit_service = ScheduleAuditService(db)
                audit_service.log_skip(UUID(sync_def_id), "Previous run still active")
            except Exception as e:
                logger.error(f"Failed to log skip: {e}")
            finally:
                db.close()
            return None

        # Release lock immediately (will be re-acquired by actual task)
        lock.release()
        return super().apply_async(args, kwargs, **options)

@celery_app.task(bind=True)
def run_push_sync(self, sync_def_id: str, trigger_type: str = "MANUAL"):
    logger.info(f"Starting push sync for definition {sync_def_id} (trigger: {trigger_type})")

    db = SessionLocal()
    run = None
    try:
        sync_def = db.get(SyncDefinition, UUID(sync_def_id))
        if not sync_def:
            logger.error(f"Sync definition {sync_def_id} not found")
            return "Failed: Definition not found"

        logger.info(f"Syncing '{sync_def.name}' (Mode: {sync_def.sync_mode})")

        history_service = RunHistoryService(db)
        run = history_service.start_run(
            sync_def.id,
            "PUSH",
            trigger_type=trigger_type,
            celery_task_id=self.request.id
        )

        pusher = Pusher(db)
        result = pusher.run_push(sync_def.id)

        logger.info(f"Push sync for {sync_def_id} completed successfully: {result}")
        history_service.end_run(run.id, "COMPLETED", items_processed=result.get("processed_count", 0))
        return f"Success: {result}"

    except Exception as e:
        logger.exception(f"Sync failed: {str(e)}")
        if run:
            history_service.end_run(run.id, "FAILED", error_message=str(e))
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()

@celery_app.task(bind=True)
def run_ingress_sync(self, sync_def_id: str, trigger_type: str = "MANUAL"):
    logger.info(f"Starting ingress sync for definition {sync_def_id} (trigger: {trigger_type})")

    db = SessionLocal()
    run = None
    try:
        sync_def = db.get(SyncDefinition, UUID(sync_def_id))
        if not sync_def:
            logger.error(f"Sync definition {sync_def_id} not found")
            return "Failed: Definition not found"

        if sync_def.sync_mode != "TWO_WAY":
             logger.warning(f"Skipping ingress for '{sync_def.name}' (Mode: {sync_def.sync_mode})")
             return "Skipped: Not TWO_WAY"

        logger.info(f"Ingesting '{sync_def.name}'")

        history_service = RunHistoryService(db)
        run = history_service.start_run(
            sync_def.id,
            "INGRESS",
            trigger_type=trigger_type,
            celery_task_id=self.request.id
        )

        syncer = Synchronizer(db)
        result = syncer.run_ingress(sync_def.id)

        logger.info(f"Ingress sync for {sync_def_id} completed successfully: {result}")
        history_service.end_run(run.id, "COMPLETED", items_processed=result.get("processed_count", 0))
        return f"Success: {result}"

    except Exception as e:
        logger.exception(f"Ingress failed: {str(e)}")
        if run:
            history_service.end_run(run.id, "FAILED", error_message=str(e))
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, base=SingletonTask)
def run_scheduled_sync(self, sync_def_id: str):
    """
    Wrapper task for scheduled syncs with concurrent execution prevention.
    """
    logger.info(f"Starting scheduled sync for definition {sync_def_id}")

    lock_key = f"sync_lock:{sync_def_id}"
    lock = redis_client.lock(lock_key, timeout=3600)

    if not lock.acquire(blocking=False):
        logger.warning(f"Sync {sync_def_id} already running, skipping")
        return "Skipped: Already running"

    db = SessionLocal()
    try:
        sync_def = db.get(SyncDefinition, UUID(sync_def_id))
        if not sync_def:
            logger.error(f"Sync definition {sync_def_id} not found")
            return "Failed: Definition not found"

        if not sync_def.schedule_enabled or sync_def.is_paused:
            logger.info(f"Sync {sync_def_id} is paused or schedule disabled, skipping")
            return "Skipped: Paused or disabled"

        # Update last_scheduled_run
        sync_def.last_scheduled_run = datetime.utcnow()
        db.commit()

        results = {}

        # Run Push
        logger.info(f"Triggering push sync for {sync_def_id}")
        push_result = run_push_sync.apply_async(
            args=[sync_def_id],
            kwargs={"trigger_type": "SCHEDULED"}
        )
        results["push_task_id"] = push_result.id if push_result else None

        # Run Ingress if TWO_WAY
        if sync_def.sync_mode == "TWO_WAY":
            logger.info(f"Triggering ingress sync for {sync_def_id}")
            ingress_result = run_ingress_sync.apply_async(
                args=[sync_def_id],
                kwargs={"trigger_type": "SCHEDULED"}
            )
            results["ingress_task_id"] = ingress_result.id if ingress_result else None

        return results

    except Exception as e:
        logger.exception(f"Scheduled sync failed: {str(e)}")
        raise
    finally:
        lock.release()
        db.close()


@celery_app.task(bind=True)
def reconcile_drift_metrics(self):
    """
    Background task to reconcile drift metrics for all active sync definitions.
    Calculates source vs target row counts and updates sync_metrics table.
    Run periodically (e.g., every 15-30 minutes) via Celery Beat.
    """
    logger.info("Starting drift reconciliation for all syncs")

    lock_key = "drift_reconciliation_lock"
    lock = redis_client.lock(lock_key, timeout=1800)  # 30 min max

    if not lock.acquire(blocking=False):
        logger.warning("Drift reconciliation already running, skipping")
        return "Skipped: Already running"

    db = SessionLocal()
    try:
        reconciliation_service = ReconciliationService(db)
        summary = reconciliation_service.reconcile_all_syncs()

        logger.info(
            f"Drift reconciliation completed: {summary['reconciled']} succeeded, "
            f"{summary['failed']} failed out of {summary['total_syncs']} total syncs"
        )

        if summary['errors']:
            logger.warning(f"Errors during reconciliation: {summary['errors']}")

        return summary

    except Exception as e:
        logger.exception(f"Drift reconciliation failed: {str(e)}")
        raise
    finally:
        lock.release()
        db.close()


@celery_app.task(bind=True)
def reconcile_single_sync(self, sync_def_id: str):
    """
    Reconcile drift metrics for a single sync definition.
    Can be triggered on-demand or after sync completion.
    """
    logger.info(f"Reconciling drift for sync {sync_def_id}")

    db = SessionLocal()
    try:
        reconciliation_service = ReconciliationService(db)
        metric = reconciliation_service.reconcile_sync(UUID(sync_def_id))

        logger.info(
            f"Drift reconciliation for {sync_def_id} completed: "
            f"source={metric.source_row_count}, target={metric.target_row_count}, "
            f"delta={metric.reconcile_delta}, status={metric.reconcile_status}"
        )

        return {
            "sync_def_id": str(sync_def_id),
            "source_count": metric.source_row_count,
            "target_count": metric.target_row_count,
            "delta": metric.reconcile_delta,
            "status": metric.reconcile_status
        }

    except Exception as e:
        logger.exception(f"Failed to reconcile sync {sync_def_id}: {str(e)}")
        raise
    finally:
        db.close()


@celery_app.task
def dispatch_sync_schedules():
    from app.services.schedule_dispatch import dispatch_due_schedules

    db = SessionLocal()
    try:
        return dispatch_due_schedules(db, run_scheduled_sync.delay)
    finally:
        db.close()
