import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, JSON, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.db.base import Base

class DatabaseInstance(Base):
    """
    Represents physical database endpoints. Multiple instances allow multi-source sync
    and location changes without recreating sync items.
    """
    __tablename__ = "database_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    database_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("databases.id", ondelete="CASCADE"),
        nullable=True  # Made optional for backward compatibility
    )
    instance_label: Mapped[str] = mapped_column(String, unique=True)
    host: Mapped[str] = mapped_column(String)
    port: Mapped[int] = mapped_column(Integer, default=5432)
    database_name_override: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Credentials
    db_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    password: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Encrypted

    # Config
    config: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Role and status
    role: Mapped[str] = mapped_column(String, default="PRIMARY") # PRIMARY, SECONDARY
    priority: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String, default="ACTIVE") # ACTIVE, DISABLED

    # Timestamps
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # CDC Metadata
    replication_slot_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_wal_lsn: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    database: Mapped[Optional["Database"]] = relationship("Database", back_populates="instances")
    sync_sources: Mapped[List["SyncSource"]] = relationship(
        back_populates="database_instance",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    source_table_metrics: Mapped[List["SourceTableMetric"]] = relationship(
        "SourceTableMetric",
        back_populates="database_instance",
        cascade="all, delete-orphan",
        foreign_keys="SourceTableMetric.database_instance_id"
    )
    introspection_runs: Mapped[List["IntrospectionRun"]] = relationship(
        "IntrospectionRun",
        back_populates="database_instance",
        cascade="all, delete-orphan",
        foreign_keys="IntrospectionRun.database_instance_id"
    )
    schema_snapshots: Mapped[List["SchemaSnapshot"]] = relationship(
        "SchemaSnapshot",
        back_populates="database_instance",
        cascade="all, delete-orphan",
        foreign_keys="SchemaSnapshot.database_instance_id"
    )


class SharePointConnection(Base):
    __tablename__ = "sharepoint_connections"
    __table_args__ = (
        UniqueConstraint("tenant_id", "client_id", name="uq_sharepoint_connections_tenant_client"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String)
    client_id: Mapped[str] = mapped_column(String)
    client_secret: Mapped[Optional[str]] = mapped_column(String, nullable=True) # TODO: Encrypt this
    authority_host: Mapped[str] = mapped_column(String, default="https://login.microsoftonline.com")
    hostname: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scopes: Mapped[list] = mapped_column(JSONB) # List of scopes
    status: Mapped[str] = mapped_column(String, default="ACTIVE")

    # Relationships
    sites: Mapped[List["SharePointSite"]] = relationship(
        "SharePointSite",
        back_populates="connection",
        cascade="all, delete-orphan",
        foreign_keys="SharePointSite.connection_id"
    )


class SyncDefinition(Base):
    __tablename__ = "sync_definitions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)
    source_table_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True)) # Logical ref to table
    
    # Added to support direct mapping without Inventory tables
    source_schema: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_table_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    target_list_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True) # Default target
    sync_mode: Mapped[str] = mapped_column(String) # ONE_WAY_PUSH, TWO_WAY
    conflict_policy: Mapped[str] = mapped_column(String, default="SOURCE_WINS")
    key_strategy: Mapped[str] = mapped_column(String) # COMPOSITE_COLUMNS, PRIMARY_KEY
    key_constraint_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    target_strategy: Mapped[str] = mapped_column(String, default="SINGLE") # SINGLE, CONDITIONAL
    cursor_strategy: Mapped[str] = mapped_column(String, default="UPDATED_AT")
    cursor_column_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    sharding_policy: Mapped[dict] = mapped_column(JSONB, default={})
    
    cdc_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
    rate_limit_ms: Mapped[int] = mapped_column(Integer, default=0)

    # Scheduling Configuration
    schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_type: Mapped[Optional[str]] = mapped_column(String, nullable=True) # INTERVAL, CRON
    schedule_interval_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    schedule_cron_expression: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    schedule_timezone: Mapped[str] = mapped_column(String, default="UTC")
    last_scheduled_run: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_scheduled_run: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    sources: Mapped[List["SyncSource"]] = relationship(
        back_populates="sync_definition",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    targets: Mapped[List["SyncTarget"]] = relationship(
        back_populates="sync_definition",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    key_columns: Mapped[List["SyncKeyColumn"]] = relationship(
        back_populates="sync_definition",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    field_mappings: Mapped[List["FieldMapping"]] = relationship(
        back_populates="sync_definition",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class SyncSource(Base):
    __tablename__ = "sync_sources"

    sync_def_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sync_definitions.id", ondelete="CASCADE"), primary_key=True)
    database_instance_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("database_instances.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String, default="PRIMARY")
    priority: Mapped[int] = mapped_column(Integer, default=1)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    sync_definition: Mapped["SyncDefinition"] = relationship(back_populates="sources")
    database_instance: Mapped["DatabaseInstance"] = relationship(back_populates="sync_sources")


class SyncTarget(Base):
    __tablename__ = "sync_targets"

    sync_def_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sync_definitions.id", ondelete="CASCADE"), primary_key=True)
    target_list_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True) # Maps to a SP List (external ID or internal ref)
    
    sharepoint_connection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("sharepoint_connections.id", ondelete="CASCADE"),
        nullable=True,
    )
    site_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String, default="ACTIVE")

    sync_definition: Mapped["SyncDefinition"] = relationship(back_populates="targets")
    connection: Mapped["SharePointConnection"] = relationship()


class SyncKeyColumn(Base):
    __tablename__ = "sync_key_columns"

    sync_def_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sync_definitions.id", ondelete="CASCADE"), primary_key=True)
    column_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    ordinal_position: Mapped[int] = mapped_column(Integer)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)

    sync_definition: Mapped["SyncDefinition"] = relationship(back_populates="key_columns")


class FieldMapping(Base):
    __tablename__ = "field_mappings"
    __table_args__ = (
        UniqueConstraint(
            "sync_def_id",
            "source_column_id",
            "target_column_id",
            name="uq_field_mappings_sync_source_target",
        ),
        Index("ix_field_mappings_sync_def_id", "sync_def_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_def_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sync_definitions.id", ondelete="CASCADE"))
    source_column_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    target_column_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))

    # Added to support direct mapping without Inventory tables
    source_column_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    target_column_name: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Internal Name in SharePoint

    target_type: Mapped[str] = mapped_column(String)
    transform_rule: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_key: Mapped[bool] = mapped_column(Boolean, default=False)
    is_readonly: Mapped[bool] = mapped_column(Boolean, default=False)

    # Phase 6: Directional Mapping
    # Values: BIDIRECTIONAL (default), PUSH_ONLY (source->target), PULL_ONLY (target->source)
    sync_direction: Mapped[str] = mapped_column(String, default="BIDIRECTIONAL")

    # Phase 6: System Field Support (for SharePoint readonly fields like ID, Created, Modified)
    is_system_field: Mapped[bool] = mapped_column(Boolean, default=False)

    sync_definition: Mapped["SyncDefinition"] = relationship(back_populates="field_mappings")


class SyncCursor(Base):
    __tablename__ = "sync_cursors"
    __table_args__ = (
        Index("ix_sync_cursors_sync_scope_updated", "sync_def_id", "cursor_scope", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_def_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sync_definitions.id", ondelete="CASCADE"))
    cursor_scope: Mapped[str] = mapped_column(String) # SOURCE, TARGET
    cursor_type: Mapped[str] = mapped_column(String) # TIMESTAMP, LSN, DELTA_TOKEN
    cursor_value: Mapped[str] = mapped_column(String)
    
    source_instance_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    target_list_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SyncLedgerEntry(Base):
    __tablename__ = "sync_ledger"
    __table_args__ = (
        Index("ix_sync_ledger_sync_source_instance", "sync_def_id", "source_instance_id"),
    )

    sync_def_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    source_identity_hash: Mapped[str] = mapped_column(String, primary_key=True) # SHA256
    source_identity: Mapped[str] = mapped_column(String) # Printable identity
    source_key_strategy: Mapped[str] = mapped_column(String)
    source_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    
    sp_list_id: Mapped[str] = mapped_column(String) # GUID
    sp_item_id: Mapped[int] = mapped_column(Integer)
    
    content_hash: Mapped[str] = mapped_column(String) # SHA256 of payload
    last_source_ts: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    provenance: Mapped[str] = mapped_column(String) # PUSH, PULL


class MoveAuditLog(Base):
    __tablename__ = "move_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_def_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    source_identity_hash: Mapped[str] = mapped_column(String)
    
    from_list_id: Mapped[str] = mapped_column(String)
    to_list_id: Mapped[str] = mapped_column(String)
    
    moved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String, default="SUCCESS") # SUCCESS, FAILED_ORPHAN
    details: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Error msg or additional info

class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_def_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    run_type: Mapped[str] = mapped_column(String) # PUSH, INGRESS, CDC
    status: Mapped[str] = mapped_column(String) # RUNNING, COMPLETED, FAILED
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    items_processed: Mapped[int] = mapped_column(Integer, default=0)
    items_failed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Trigger tracking
    trigger_type: Mapped[str] = mapped_column(String, default="MANUAL") # MANUAL, SCHEDULED, CDC
    celery_task_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class CeleryPeriodicTask(Base):
    """
    Application schedule metadata used by the periodic dispatch task
    """
    __tablename__ = "celery_periodic_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True)  # e.g., "sync_def_{uuid}_scheduled"
    task: Mapped[str] = mapped_column(String)  # "app.worker.tasks.run_scheduled_sync"

    # Schedule Config (one of these)
    interval_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    crontab_minute: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    crontab_hour: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    crontab_day_of_week: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    crontab_day_of_month: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    crontab_month_of_year: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Task Arguments
    args: Mapped[list] = mapped_column(JSONB, default=list)  # [sync_def_id]
    kwargs: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Metadata
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_run_count: Mapped[int] = mapped_column(Integer, default=0)
    date_changed: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Reference back to sync definition
    sync_def_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("sync_definitions.id", ondelete="CASCADE"),
        nullable=True
    )


class ScheduledSyncAudit(Base):
    """
    Tracks scheduled sync execution for monitoring and alerting
    """
    __tablename__ = "scheduled_sync_audit"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_def_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sync_definitions.id", ondelete="CASCADE"))
    periodic_task_id: Mapped[int] = mapped_column(Integer)

    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # When it should run
    actual_start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completion_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String)  # SCHEDULED, RUNNING, COMPLETED, FAILED, SKIPPED
    skip_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # "Previous run still active"
    sync_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)  # Link to SyncRun

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SyncAlert(Base):
    """
    In-app alerts for sync issues
    """
    __tablename__ = "sync_alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sync_def_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sync_definitions.id", ondelete="CASCADE"))
    alert_type: Mapped[str] = mapped_column(String)  # CONSECUTIVE_FAILURES, CDC_LAG, SCHEDULE_SKIP
    severity: Mapped[str] = mapped_column(String)  # WARNING, ERROR, CRITICAL
    message: Mapped[str] = mapped_column(String)
    alert_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
