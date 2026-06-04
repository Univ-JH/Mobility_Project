from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple, Optional
from app.repositories.models import Device, Event
from app.domain.states import DeviceState
from app.core.database import get_db
import pymongo

async def get_dashboard_stats() -> Dict[str, Any]:
    # 1. Active Devices
    five_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
    active_devices = await Device.find(Device.lastSeenAt >= five_mins_ago).count()
    
    # 2. Emergencies Today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    emergencies_today = await Event.find(
        Event.eventAt >= today_start,
        Event.eventType == "emergency"
    ).count()
    
    # 3. Helmet Compliance (from Device model)
    total_devices = await Device.find().count()
    helmet_worn_devices = await Device.find(Device.helmetWorn == True).count()
    helmet_compliance = (helmet_worn_devices / total_devices * 100) if total_devices > 0 else 0.0
    
    # 4. Avg Battery
    # We can aggregate from recent telemetry events (payload.health.batteryPct)
    pipeline = [
        {"$match": {"eventAt": {"$gte": today_start}, "payload.health.batteryPct": {"$exists": True}}},
        {"$group": {"_id": None, "avg_battery": {"$avg": "$payload.health.batteryPct"}}}
    ]
    battery_res = [doc async for doc in get_db()[Event.Settings.name].aggregate(pipeline)]
    avg_battery = battery_res[0]["avg_battery"] if battery_res else 0.0
    
    return {
        "activeDevices": active_devices,
        "emergenciesToday": emergencies_today,
        "helmetCompliance": helmet_compliance,
        "avgBattery": avg_battery
    }

async def get_active_locations() -> List[Device]:
    five_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
    return await Device.find(
        Device.lastSeenAt >= five_mins_ago,
        Device.lastLocation != None
    ).to_list()

async def get_alerts_timeline() -> List[Dict[str, Any]]:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    pipeline = [
        {"$match": {
            "eventAt": {"$gte": today_start},
            "severity": {"$in": ["medium", "high", "critical"]}
        }},
        {"$project": {
            "hour": {"$dateToString": {"format": "%H:00", "date": "$eventAt"}}
        }},
        {"$group": {
            "_id": "$hour",
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    res = [doc async for doc in get_db()[Event.Settings.name].aggregate(pipeline)]
    return [{"time": r["_id"], "count": r["count"]} for r in res]

async def get_environment_stats() -> Dict[str, float]:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    pipeline = [
        {"$match": {
            "eventAt": {"$gte": today_start},
            "payload.vision.surfaceClass": {"$in": ["sidewalk", "road"]}
        }},
        {"$group": {
            "_id": "$payload.vision.surfaceClass",
            "count": {"$sum": 1}
        }}
    ]
    res = [doc async for doc in get_db()[Event.Settings.name].aggregate(pipeline)]

    counts = {"sidewalk": 0, "road": 0}
    for r in res:
        counts[r["_id"]] = r["count"]
        
    total = counts["sidewalk"] + counts["road"]
    if total == 0:
        return {"sidewalkRatio": 0.0, "roadRatio": 0.0}
        
    return {
        "sidewalkRatio": counts["sidewalk"] / total * 100,
        "roadRatio": counts["road"] / total * 100
    }

async def get_paginated_events(page: int, size: int, severity: Optional[str] = None) -> Tuple[List[Event], int]:
    query = Event.find()
    if severity:
        query = query.find(Event.severity == severity)
        
    total_count = await query.count()
    items = await query.sort(-Event.eventAt).skip((page - 1) * size).limit(size).to_list()
    
    return items, total_count

async def get_all_events_for_export() -> List[Event]:
    return await Event.find().sort(-Event.eventAt).to_list()
