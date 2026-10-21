# Review findings and functionality opportunities

## Implemented

- Restored frontend utilities and Mermaid generators missing from the checkout. The Python `lib/` ignore rule also hid frontend helpers; explicit exceptions now keep them visible to Git. Diagram labels are escaped and Mermaid uses strict security settings.
- Declared SQLAlchemy's asyncio extra, required when importing SQLAdmin on a clean install.
- Replaced the incompatible third-party Beat database scheduler with a periodic dispatcher that reads the application's existing schedule tables. Workers explicitly import the task module.
- Validate five-field cron expressions, realizable dates, interval storage bounds, and IANA timezones before modifying schedule records. Next-run calculations use the selected timezone and return UTC instants.
- Clear saved schedule configuration atomically on deletion; disabling retains it for reuse.
- Share the standard database dependency for schedule routes and bound audit queries to 1–200 results.
- Added an authenticated `POST /api/v1/schedules/preview` endpoint returning five UTC timestamps without persisting configuration. The schedule editor previews these in the selected timezone, debounces edits, and discards stale responses.
- Added scheduling regression tests and included frontend tests in CI.

## Scheduling operations

Run one Celery Beat process and workers consuming both `default` and `sync_queue`, as configured in Docker Compose. Restart Beat and workers after upgrading. No database migration is required.

Beat queues `dispatch_sync_schedules` every 15 seconds. The dispatcher locks due schedule records, rechecks eligibility, publishes scheduled sync tasks, and advances their next-run times. Disabled tasks and paused definitions are excluded. Records with no next-run timestamp are initialized without firing immediately. Missed occurrences are coalesced into one execution, with the next occurrence calculated from the dispatch time.

Publishing failures leave records due for the next attempt. Delivery is at least once: a process crash after broker publication but before database commit can redeliver a task. PostgreSQL row locking coordinates concurrent dispatchers; SQLite regression tests verify behavior but do not exercise PostgreSQL lock contention. Live PostgreSQL/Redis/Graph integration remains a deployment check.

## Next functionality opportunities

1. **Run Retry Center:** implement the existing feature specification with retry reason, actor, lineage, and concurrent retry protection. This would make failure recovery accessible from run history.
2. **Execution-wide concurrency control:** hold per-definition ownership across the complete push/ingress task chain, including retries. The current scheduled wrapper lock ends after enqueueing its child tasks.
3. **Transactional scheduling outbox:** persist dispatch intents with occurrence IDs, then publish and deduplicate them. This would close the broker-publication/database-commit crash window.
4. **Schedule audit and alerts:** connect scheduled run completion to audit records and notify operators about repeated failures, skipped runs, and stale next-run timestamps.
