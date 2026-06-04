import json
from datetime import datetime, timezone
import uuid
import aiomqtt
from app.core.config import settings
from app.repositories.models import ControlCommandLog

async def publish_control_command(device_id: str, action: str, params: dict = None, reason: str = "Automated control"):
    """
    Publish MQTT control commands to the device.
    Topic: device/{deviceId}/control
    """
    command_id = str(uuid.uuid4())
    topic = f"device/{device_id}/control"
    
    payload = {
        "schemaVersion": 1,
        "commandId": command_id,
        "action": action,
        "params": params or {},
        "reason": reason,
        "ttlMs": 5000,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # 1. Create ControlCommandLog (PENDING)
    log_doc = ControlCommandLog(
        commandId=command_id,
        deviceId=device_id,
        command=action,
        params=params or {},
        reason=reason,
        status="PENDING"
    )
    await log_doc.insert()
    
    # 2. Publish to MQTT Broker
    try:
        async with aiomqtt.Client(
            hostname=settings.MQTT_BROKER_URL,
            port=settings.MQTT_PORT,
            identifier=f"{settings.MQTT_CLIENT_ID}-pub-{uuid.uuid4().hex[:8]}"
        ) as client:
            await client.publish(
                topic=topic,
                payload=json.dumps(payload),
                qos=1
            )
            print(f"[MQTT Publish] Topic: {topic} | Action: {action}")
            # Update log status
            log_doc.status = "ACKED"  # In a real scenario, this might wait for a separate ack message
            log_doc.ackAt = datetime.now(timezone.utc)
            await log_doc.save()
            return True
            
    except Exception as e:
        print(f"[MQTT Publish Error] Failed to publish to {topic}: {e}")
        log_doc.status = "FAILED"
        log_doc.result = str(e)
        await log_doc.save()
        return False
