from uuid import UUID
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict, Field

from app.api.responses import success_response
from app.core.security import OPERATOR_ROLES, VIEWER_ROLES, Principal, require_roles
from app.db.session import get_db
from app.schemas.api import ApiResponse
from app.services.audit import record_audit_event
from app.services.schedule_service import ScheduleService
from app.services.schedule_audit import ScheduleAuditService


router = APIRouter()


# Schemas
class ScheduleConfig(BaseModel):
    schedule_type: str = Field(..., pattern="^(INTERVAL|CRON)$")
    interval_seconds: Optional[int] = Field(None, ge=60, le=2_147_483_647)
    cron_expression: Optional[str] = None
    timezone: str = "UTC"


class ScheduleResponse(BaseModel):
    message: str
    next_run: Optional[datetime] = None


class AuditLogResponse(BaseModel):
    id: UUID
    sync_def_id: UUID
    scheduled_time: datetime
    actual_start_time: Optional[datetime]
    completion_time: Optional[datetime]
    status: str
    skip_reason: Optional[str]
    sync_run_id: Optional[UUID]

    model_config = ConfigDict(from_attributes=True)


# Endpoints
@router.post("/preview", response_model=List[datetime])
def preview_schedule(
    config: ScheduleConfig,
    _: Principal = Depends(require_roles(*VIEWER_ROLES)),
):
    """Preview five upcoming executions without saving a schedule."""
    try:
        return ScheduleService.preview_schedule(**config.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{sync_def_id}/enable", response_model=ScheduleResponse)
def enable_schedule(
    sync_def_id: UUID,
    config: ScheduleConfig,
    request: Request,
    principal: Principal = Depends(require_roles(*OPERATOR_ROLES)),
    db: Session = Depends(get_db)
):
    """Enable scheduled sync for a sync definition."""
    service = ScheduleService(db)
    try:
        result = service.enable_schedule(
            sync_def_id,
            config.schedule_type,
            config.interval_seconds,
            config.cron_expression,
            config.timezone
        )
        record_audit_event(
            db,
            request,
            principal,
            action="schedule.enable",
            resource_type="sync_definition",
            resource_id=str(sync_def_id),
            details=config.model_dump(exclude_none=True),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{sync_def_id}/disable", response_model=ScheduleResponse)
def disable_schedule(
    sync_def_id: UUID,
    request: Request,
    principal: Principal = Depends(require_roles(*OPERATOR_ROLES)),
    db: Session = Depends(get_db),
):
    """Disable scheduled sync for a sync definition."""
    service = ScheduleService(db)
    try:
        result = service.disable_schedule(sync_def_id)
        record_audit_event(
            db,
            request,
            principal,
            action="schedule.disable",
            resource_type="sync_definition",
            resource_id=str(sync_def_id),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{sync_def_id}")
def delete_schedule(
    sync_def_id: UUID,
    request: Request,
    principal: Principal = Depends(require_roles(*OPERATOR_ROLES)),
    db: Session = Depends(get_db),
):
    """Delete schedule for a sync definition."""
    service = ScheduleService(db)
    try:
        result = service.delete_schedule(sync_def_id)
        record_audit_event(
            db,
            request,
            principal,
            action="schedule.delete",
            resource_type="sync_definition",
            resource_id=str(sync_def_id),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{sync_def_id}/audit", response_model=ApiResponse[List[AuditLogResponse]])
def get_schedule_audit(
    sync_def_id: UUID,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    _: Principal = Depends(require_roles(*VIEWER_ROLES)),
    db: Session = Depends(get_db)
):
    """Get schedule audit logs for a sync definition."""
    service = ScheduleAuditService(db)
    return success_response(request, service.get_recent_audits(sync_def_id, limit))
