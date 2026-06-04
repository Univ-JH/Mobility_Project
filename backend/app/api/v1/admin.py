from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Any, Optional

from app.api.deps import get_current_admin
from app.schemas.common import create_success_response
from app.services import admin_service

router = APIRouter()

# Apply get_current_admin dependency to all routes in this router
# by passing it in router config or router inclusion. We will do it in router.py 
# but it's safer to add dependencies=[Depends(get_current_admin)] directly to router init.

router = APIRouter(dependencies=[Depends(get_current_admin)])

@router.get("/stats")
async def read_dashboard_stats() -> Any:
    stats = await admin_service.get_dashboard_stats()
    return create_success_response(data=stats.model_dump(), message="통계 조회 성공")

@router.get("/devices/locations")
async def read_device_locations() -> Any:
    locations = await admin_service.get_active_locations()
    return create_success_response(data=[l.model_dump() for l in locations], message="위치 조회 성공")

@router.get("/analytics/alerts-timeline")
async def read_alerts_timeline() -> Any:
    timeline = await admin_service.get_alerts_timeline()
    return create_success_response(data=[b.model_dump() for b in timeline.timeline], message="타임라인 조회 성공")

@router.get("/analytics/environment")
async def read_environment_stats() -> Any:
    stats = await admin_service.get_environment_stats()
    return create_success_response(data=stats.model_dump(), message="환경 통계 조회 성공")

@router.get("/events")
async def read_events(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    severity: Optional[str] = Query(None)
) -> Any:
    paginated_events = await admin_service.get_event_logs(page, size, severity)
    return create_success_response(data=paginated_events.model_dump(), message="이벤트 로그 조회 성공")

@router.get("/export/logs")
async def export_logs() -> StreamingResponse:
    csv_stream = await admin_service.get_events_csv_stream()
    
    response = StreamingResponse(iter([csv_stream.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=events_export.csv"
    return response
