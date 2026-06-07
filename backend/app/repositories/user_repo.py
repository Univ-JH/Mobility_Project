from typing import List, Dict, Any, Optional
from datetime import datetime
from app.repositories.models import User, Event, Device

async def get_user_by_id(user_id: str) -> Optional[User]:
    return await User.find_one(User.userId == user_id)

async def create_user(user_in: User) -> User:
    await user_in.insert()
    return user_in

async def get_ride_history_for_user(user_id: str) -> List[Dict[str, Any]]:
    # Get user's devices
    devices = await Device.find(Device.ownerUserId == user_id).to_list()
    device_ids = [d.deviceId for d in devices]
    
    if not device_ids:
        return []
        
    pipeline = [
        {"$match": {"deviceId": {"$in": device_ids}}},
        {"$group": {
            "_id": "$rideId",
            "startTime": {"$min": "$eventAt"},
            "endTime": {"$max": "$eventAt"},
            "alertCount": {
                "$sum": {
                    "$cond": [{"$in": ["$severity", ["medium", "high", "critical"]]}, 1, 0]
                }
            }
        }},
        {"$sort": {"startTime": -1}}
    ]
    
    cursor = Event.get_motor_collection().aggregate(pipeline)
    res = await cursor.to_list(length=None)

    history = []
    for r in res:
        if not r.get("_id"):
            continue

        start = r.get("startTime")
        end = r.get("endTime")
        if not start:
            continue

        duration = 0.0
        if end:
            delta = end - start
            duration = delta.total_seconds() / 60.0

        history.append({
            "rideId": r["_id"],
            "startTime": start,
            "endTime": end or start,
            "durationMinutes": duration,
            "alertCount": r.get("alertCount", 0)
        })
        
    return history
