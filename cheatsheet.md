# ArcoreSyncBridge Integration Cheatsheet

- Path: `/home/jare16/Projects/ArcoreAgent/All_Arcore_Repos/ArcoreSyncBridge`
- Generated at: `2026-05-12 21:23:57Z`
- Branch: `main`
- Remote: `https://github.com/jare20895/ArcoreSyncBridge.git`
- Last commit: `aab8f0b6c2b454a2b1bd6319329a2b00019c98a4`
- Commit date: `2026-04-17 19:52:36 -0400`
- Commit subject: `chore: expand AID to full 18-section standard`

- Language mix (top): `py:123, md:93, tsx:46, [no_ext]:6, json:5, js:5, ts:5, sh:4, yml:3, ini:3, txt:2, sql:2`

## Quick Integration Pointers

### Docker services
- db: 5465:5432 (from docker-compose.yml)
- redis: 6384:6379 (from docker-compose.yml)
- backend: 8401:8401 (from docker-compose.yml)
- frontend: 3005:3000 (from docker-compose.yml)
- celery_worker: n/a (from docker-compose.yml)
- celery_beat: n/a (from docker-compose.yml)
- cdc_consumer: n/a (from docker-compose.yml)

### Run commands
- `make frontend-lint`
- `make frontend-typecheck`
- `make frontend-build`
- `make backend-test`
- `make ci`

### Recent commits

- aab8f0b chore: expand AID to full 18-section standard
- 473d143 Add Application Intelligence Document (AID)
- 8d823f8 Add frontend auth governance and pagination tests
- 2d6580c Remove backend deprecation warnings
- 9682c6f Replace remaining native dialog flows

### Integration touchpoints

- `Makefile`
- `backend/Dockerfile`
- `backend/app/api/endpoints/applications.py`
- `backend/app/api/endpoints/audit.py`
- `backend/app/api/endpoints/auth.py`
- `backend/app/api/endpoints/cdc.py`
- `backend/app/api/endpoints/data_sources.py`
- `backend/app/api/endpoints/data_targets.py`
- `backend/app/api/endpoints/database_instances.py`
- `backend/app/api/endpoints/databases.py`
- `backend/app/api/endpoints/field_mappings.py`
- `backend/app/api/endpoints/health.py`
- `backend/app/api/endpoints/metrics.py`
- `backend/app/api/endpoints/moves.py`
- `backend/app/api/endpoints/ops.py`
- `backend/app/api/endpoints/provisioning.py`
- `backend/app/api/endpoints/replication.py`
- `backend/app/api/endpoints/runs.py`
- `backend/app/api/endpoints/schedules.py`
- `backend/app/api/endpoints/sharepoint_connections.py`
- `backend/app/api/endpoints/sharepoint_discovery.py`
- `backend/app/api/endpoints/sync_definitions.py`
- `backend/app/api/responses.py`
- `backend/app/schemas/api.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/sync_definition.py`
- `backend/app/services/audit.py`
- `backend/app/services/cdc.py`
- `backend/app/services/cdc_consumer.py`
- `backend/app/services/cdc_manager.py`
- `backend/app/services/database.py`
- `backend/app/services/drift.py`
- `backend/app/services/failover.py`
- `backend/app/services/graph.py`
- `backend/app/services/introspection.py`
- `backend/app/services/maintenance.py`
- `backend/app/services/mover.py`
- `backend/app/services/pgoutput.py`
- `backend/app/services/provisioner.py`
- `backend/app/services/publication.py`
- `backend/app/services/pusher.py`
- `backend/app/services/reconciliation.py`
- `backend/app/services/replication.py`
- `backend/app/services/run_history.py`
- `backend/app/services/schedule_audit.py`
- `backend/app/services/schedule_service.py`
- `backend/app/services/secrets.py`
- `backend/app/services/sharding.py`
- `backend/app/services/sharepoint_content.py`
- `backend/app/services/sharepoint_discovery.py`
- `backend/app/services/state.py`
- `backend/app/services/synchronizer.py`
- `backend/app/worker/cdc_consumer_worker.py`
- `backend/app/worker/celery_app.py`
- `backend/app/worker/tasks.py`
- `backend/requirements.txt`
- `backend/tests/api/test_database_instances.py`
- `backend/tests/api/test_health.py`
- `backend/tests/services/test_integration_twoway.py`
- `backend/tests/services/test_mover.py`
- `backend/tests/services/test_publication.py`
- `backend/tests/services/test_sharding.py`
- `docker-compose.yml`
- `docs/FeatureSpecs/SyncDefinitionWizard.md`
- `docs/SYNCArchitecture.md`
- `docs/design/api/README.md`
- `docs/design/api/auth.md`
- `docs/design/api/endpoints.md`
- `docs/design/architecture/diagrams/api_interactions.md`
- `docs/design/architecture/diagrams/service_dependencies.md`
- `docs/design/architecture/diagrams/sync_flow_one_way.md`
- `docs/design/architecture/diagrams/sync_flow_two_way.md`
- `docs/design/architecture/security/authentication_flows.md`
- `docs/design/process/delivery/ci_cd_pipeline.md`
- `docs/design/templates/api_reference_template.md`
- `frontend/package.json`
- `frontend/src/__tests__/components/AuthGate.test.tsx`
- `frontend/src/components/auth/AuthGate.tsx`
- `frontend/src/components/auth/AuthProvider.tsx`
- `frontend/src/components/diagrams/AllSyncsGridView.tsx`

## Main API Endpoints (best-effort)

High-confidence endpoints:

Additional endpoints (lower confidence):
- GET    /  [medium]   (backend/app/main.py:157)  from framework-router
- GET    /admin-check  [medium]   (backend/app/api/endpoints/auth.py:38)  from framework-router
- GET    /applications/  [medium]   (frontend/src/services/api.ts:76)  from framework-router
- GET    /auth/config  [medium]   (frontend/src/services/api.ts:422)  from framework-router
- GET    /auth/me  [medium]   (frontend/src/services/api.ts:417)  from framework-router
- GET    /cdc-health  [medium]   (backend/app/api/endpoints/health.py:30)  from framework-router
- GET    /config  [medium]   (backend/app/api/endpoints/auth.py:20)  from framework-router
- GET    /connections  [medium]   (backend/app/api/endpoints/provisioning.py:133)  from framework-router
- GET    /counts  [medium]   (backend/app/api/endpoints/metrics.py:22)  from framework-router
- GET    /database-instances/  [medium]   (frontend/src/services/api.ts:151)  from framework-router
- GET    /database-stats  [medium]   (backend/app/api/endpoints/health.py:45)  from framework-router
- GET    /debug-token/{connection_id}  [medium]   (backend/app/api/endpoints/provisioning.py:152)  from framework-router
- GET    /drift-metrics  [medium]   (backend/app/api/endpoints/metrics.py:172)  from framework-router
- GET    /drift-summary  [medium]   (backend/app/api/endpoints/metrics.py:154)  from framework-router
- GET    /health  [medium]   (backend/app/main.py:140)  from framework-router
- GET    /health/cdc-health  [medium]   (frontend/src/services/api.ts:537)  from framework-router
- GET    /health/database-stats  [medium]   (frontend/src/services/api.ts:542)  from framework-router
- GET    /lists/by-source  [medium]   (backend/app/api/endpoints/data_targets.py:69)  from framework-router
- GET    /lists/{list_id}/columns  [medium]   (backend/app/api/endpoints/data_targets.py:327)  from framework-router
- GET    /me  [medium]   (backend/app/api/endpoints/auth.py:33)  from framework-router
- GET    /metrics/counts  [medium]   (frontend/src/services/api.ts:566)  from framework-router
- GET    /metrics/drift-metrics  [medium]   (frontend/src/services/api.ts:584)  from framework-router
- GET    /metrics/drift-summary  [medium]   (frontend/src/services/api.ts:579)  from framework-router
- GET    /publications/{instance_id}  [medium]   (backend/app/api/endpoints/replication.py:79)  from framework-router
- GET    /publications/{instance_id}/tables  [medium]   (backend/app/api/endpoints/replication.py:92)  from framework-router
- GET    /ready  [medium]   (backend/app/main.py:145)  from framework-router
- GET    /runs/  [medium]   (frontend/src/services/api.ts:427)  from framework-router
- GET    /sharepoint-connections/  [medium]   (frontend/src/services/api.ts:232)  from framework-router
- GET    /sites  [medium]   (backend/app/api/endpoints/data_targets.py:110)  from framework-router
- GET    /sites/{site_id}/lists  [medium]   (backend/app/api/endpoints/data_targets.py:228)  from framework-router
- GET    /slots/{instance_id}  [medium]   (backend/app/api/endpoints/replication.py:19)  from framework-router
- GET    /status  [medium]   (backend/app/api/endpoints/cdc.py:161)  from framework-router
- GET    /sync-definition/{sync_def_id}  [medium]   (backend/app/api/endpoints/field_mappings.py:55)  from framework-router
- GET    /sync-definitions/  [medium]   (frontend/src/services/api.ts:335)  from framework-router
- GET    /tables  [medium]   (backend/app/api/endpoints/data_sources.py:64)  from framework-router
- GET    /tables/{table_id}  [medium]   (backend/app/api/endpoints/data_sources.py:306)  from framework-router
- GET    /users  [medium]   (backend/app/api/endpoints/auth.py:46)  from framework-router
- GET    /{application_id}  [medium]   (backend/app/api/endpoints/applications.py:48)  from framework-router
- GET    /{connection_id}  [medium]   (backend/app/api/endpoints/sharepoint_connections.py:72)  from framework-router
- GET    /{connection_id}/sites  [medium]   (backend/app/api/endpoints/sharepoint_discovery.py:78)  from framework-router

## Post-scan checks

- ⚠️ No high-confidence API map for this repo. Verify API file/docs for explicit endpoint specs.
