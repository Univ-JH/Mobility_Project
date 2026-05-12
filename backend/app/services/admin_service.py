import csv
import io
from typing import Optional
from app.repositories import admin_repo
from app.schemas.admin_dto import (
    AdminStatsResponse, DeviceLocationDto, AlertsTimelineResponse,
    AlertsTimelineBucket, EnvironmentStatsResponse, EventLogPaginatedResponse, EventLogDto
)

async def get_dashboard_stats() -> AdminStatsResponse:
    stats = await admin_repo.get_dashboard_stats()
    return AdminStatsResponse(**stats)

async def get_active_locations() -> list[DeviceLocationDto]:
    devices = await admin_repo.get_active_locations()
    locations = []
    for d in devices:
        if d.lastLocation:
            locations.append(DeviceLocationDto(
                deviceId=d.deviceId,
                lat=d.lastLocation.lat,
                lng=d.lastLocation.lng,
                state=d.currentState.value
            ))
    return locations

async def get_alerts_timeline() -> AlertsTimelineResponse:
    timeline_data = await admin_repo.get_alerts_timeline()
    buckets = [AlertsTimelineBucket(**bucket) for bucket in timeline_data]
    return AlertsTimelineResponse(timeline=buckets)

async def get_environment_stats() -> EnvironmentStatsResponse:
    stats = await admin_repo.get_environment_stats()
    return EnvironmentStatsResponse(**stats)

async def get_event_logs(page: int, size: int, severity: Optional[str]) -> EventLogPaginatedResponse:
    items, total = await admin_repo.get_paginated_events(page, size, severity)
    
    dto_items = []
    for item in items:
        # Default reason/confidence from payload if not in top level (model might have confidence top level)
        reason = item.payload.get("reason", "Unknown")
        dto_items.append(EventLogDto(
            eventId=str(item.id),
            deviceId=item.deviceId,
            eventType=item.eventType,
            severity=item.severity,
            reason=reason,
            confidence=item.confidence,
            eventAt=item.eventAt
        ))
        
    return EventLogPaginatedResponse(
        items=dto_items,
        totalCount=total,
        page=page,
        size=size
    )

async def get_events_csv_stream() -> io.StringIO:
    events = await admin_repo.get_all_events_for_export()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["Event ID", "Device ID", "Event Type", "Severity", "Confidence", "Event At", "Ingested At"])
    
    for e in events:
        writer.writerow([
            str(e.id),
            e.deviceId,
            e.eventType,
            e.severity,
            f"{e.confidence:.2f}",
            e.eventAt.isoformat(),
            e.ingestedAt.isoformat()
        ])
        
    output.seek(0)
    return output
