from typing import List, Dict, Any, Optional
from datetime import datetime
from app.repositories.models import User, Event, Device
import pymongo

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
    
    res = await Event.aggregate(pipeline).to_list()
    
    history = []
    for r in res:
        # Avoid missing rideId logic if it's null
        if not r["_id"]:
            continue
            
        duration = 0.0
        if r["endTime"] and r["startTime"]:
            delta = r["endTime"] - r["startTime"]
            duration = delta.total_seconds() / 60.0
            
        history.append({
            "rideId": r["_id"],
            "startTime": r["startTime"],
            "endTime": r["endTime"],
            "durationMinutes": duration,
            "alertCount": r["alertCount"]
        })
        
    return history
