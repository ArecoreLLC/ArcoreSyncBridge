# Arcore SyncBridge

Arcore SyncBridge is an enterprise-grade middleware service that synchronizes PostgreSQL data with SharePoint/Teams lists using Microsoft Graph. It provides a comprehensive control plane API and UI for configuration, automated sync workers for data synchronization, and a meta-store that tracks state, audit history, and operational metrics.

## Core Capabilities

### Data Synchronization
- **Bidirectional Sync**: Full two-way synchronization between PostgreSQL and SharePoint with conflict resolution
- **Real-Time CDC**: Change Data Capture using PostgreSQL logical replication for near real-time updates
- **Incremental Sync**: Cursor-based incremental updates using timestamps, LSN, or Graph delta tokens
- **Idempotent Operations**: Ledger-based tracking with content hashing prevents duplicate operations
- **Loop Prevention**: Provenance tracking (PUSH/PULL) prevents infinite sync loops

### Field Mapping & Transformation
- **Interactive Mapping Editor**: Full CRUD UI for managing field mappings
- **Directional Mapping**: Per-field sync direction control (BIDIRECTIONAL, PUSH_ONLY, PULL_ONLY)
- **Type Serialization**: Automatic conversion of Python datetime, Decimal, UUID to JSON-compatible types
- **System Field Support**: Map read-only SharePoint fields (ID, Created, Modified) to writable DB columns
- **Rich Type Support**: Handle SharePoint Choice, Person, Lookup, and complex field types

### Advanced Routing
- **Sharding Policies**: Conditional multi-list routing based on row data (e.g., route by status, date ranges)
- **Dynamic Moves**: Automatically move items between lists when sharding conditions change
- **Drift Detection**: Identify orphaned items and reconcile count mismatches

### Data Source Management
- **Multi-Source Support**: Track multiple physical database instances per logical database
- **Source Failover**: Automatic failover to secondary database instances
- **Catalog & Introspection**: Full database schema extraction for tables, columns, constraints, indexes
- **Inventory Management**: Hierarchical tracking of Applications → Databases → Instances → Tables

### Operations & Monitoring
- **Run History Dashboard**: Complete visibility into all sync executions with status, duration, item counts
- **Sync Ledger**: Audit trail of every synchronized row with content hashes and timestamps
- **Cursor Management**: Reset and manage sync cursors for testing and recovery
- **Error Tracking**: Detailed error messages and failure counts per sync run
- **Metrics & Reconciliation**: Track source vs target counts and detect drift

## Architecture Overview

### Technology Stack
- **Backend API**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 13+ with pgcrypto, logical replication
- **Frontend**: Next.js 13+ with TypeScript, TailwindCSS
- **External Integration**: Microsoft Graph API, SharePoint REST API
- **Authentication**: Azure AD with OAuth 2.0 client credentials flow

### Key Components
- **Control Plane**: REST API for configuration, catalog management, sync definitions
- **Sync Workers**: Push (DB→SharePoint), Pull (SharePoint→DB), CDC (real-time)
- **Meta-Store**: Centralized state tracking for inventory, mappings, cursors, ledger
- **Admin UI**: Modern React-based interface for operations and monitoring

## Current Status

### ✅ Completed Phases

**Phase 0: Foundation** - Repository, CI/CD, meta-store schema, observability baseline

**Phase 1: Provisioning and One-Way Sync** - Database introspection, SharePoint provisioning, push sync with cursor management

**Phase 2: Sharding and Moves** - Multi-list routing with conditional sharding, move logic, drift detection

**Phase 3: Two-Way Sync** - Bidirectional sync with Graph delta queries, conflict resolution, loop prevention

**Phase 4: Hardening and Scale** - Parallel workers, rate limiting, batching, disaster recovery runbooks

**Phase 5: Real-Time CDC and Governance** - CDC ingestion with LSN cursors, backpressure controls, run history tracking, replication slot management

**Phase 6: Advanced Mapping & Two-Way Fidelity** - Interactive mapping editor, directional mapping, system field support, type serialization, cursor reset functionality

### 🔄 In Progress

**Phase 7: Scheduled Jobs & Automation** - APScheduler integration, CRUD UI for job schedules, monitoring and notifications

### Key Features Implemented
- Complete CRUD UIs for Applications, Databases, Instances, SharePoint Connections
- Data Sources and Data Targets inventory pages
- Sync Definition management with field mapping editor
- Run History dashboard with filtering and metrics
- Drift detection and reporting
- Reset cursor functionality for testing/recovery
- Type serialization (datetime, date, Decimal, UUID)
- SharePoint GUID resolution
- Cursor advancement only on successful operations

## Quick Start

### Prerequisites
- PostgreSQL 13+ with superuser access (for CDC setup)
- Azure AD app registration with Microsoft Graph permissions
- SharePoint site with list creation permissions
- Python 3.11+ and Node.js 18+

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Populate `backend/.env` first. The tracked file now contains placeholders only.

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Docker Compose Setup
```bash
docker compose --env-file backend/.env up --build
```

### Environment Variables
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/arcore_sync

# SharePoint (can be overridden per connection in UI)
SHAREPOINT_TENANT_ID=your-tenant-id
SHAREPOINT_CLIENT_ID=your-client-id
SHAREPOINT_CLIENT_SECRET=your-client-secret
```

## Documentation

### Core Documentation
- [PHASED_CHECKLIST.md](docs/PHASED_CHECKLIST.md) - Implementation roadmap and progress tracking
- [SYNCArchitecture.md](docs/SYNCArchitecture.md) - Comprehensive sync logic and algorithms
- [PROJECT_PLAN.md](docs/PROJECT_PLAN.md) - Goals, scope, and milestones
- [DATA_MODEL.md](docs/DATA_MODEL.md) - Database schema and entity relationships
- [IMPLEMENTATION_SPECS.md](docs/IMPLEMENTATION_SPECS.md) - Technical specifications

### API & Integration
- [docs/design/api/endpoints.md](docs/design/api/endpoints.md) - REST API reference
- [docs/guides/admin/sharepoint_setup.md](docs/guides/admin/sharepoint_setup.md) - SharePoint configuration

### Operations
- [docs/guides/admin/operational_runbook.md](docs/guides/admin/operational_runbook.md) - Operations guide
- [docs/guides/admin/disaster_recovery.md](docs/guides/admin/disaster_recovery.md) - Backup and recovery
- [docs/guides/admin/release_and_rollback.md](docs/guides/admin/release_and_rollback.md) - Deployment procedures

### Development
- [docs/guides/developer/cdc_setup.md](docs/guides/developer/cdc_setup.md) - CDC configuration
- [docs/guides/developer/database_access.md](docs/guides/developer/database_access.md) - Database patterns
- [docs/design/architecture/adr/002_cdc_strategy.md](docs/design/architecture/adr/002_cdc_strategy.md) - CDC architecture decision

## Contributing
See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines.

## License
Proprietary - Arcore Internal Use Only

### Schedule preview and dispatch

The schedule editor previews five upcoming runs in the selected timezone before saving. Cron schedules use standard five-field expressions and IANA timezones. Celery Beat checks persisted schedules every 15 seconds; run one Beat process and workers consuming `default` and `sync_queue`. Restart both after upgrading.

See [review findings and opportunities](docs/REVIEW_FINDINGS.md) for delivery behavior, validation coverage, and follow-up functionality.
