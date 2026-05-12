import json
from datetime import datetime, timezone
import uuid

async def publish_control_command(device_id: str, action: str, params: dict = None):
    """
    Mock function to publish MQTT control commands to the device.
    In a real implementation, this would use a global aiomqtt.Client instance to publish.
    Topic: device/{deviceId}/control
    """
    topic = f"device/{device_id}/control"
    payload = {
        "schemaVersion": 1,
        "commandId": str(uuid.uuid4()),
        "action": action,
        "params": params or {},
        "reason": "User requested via mobile app",
        "ttlMs": 5000,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Simulate publishing
    print(f"[MQTT Mock Publish] Topic: {topic} | Payload: {json.dumps(payload)}")
    return True
