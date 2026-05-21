from app.schemas.mqtt_payloads import TelemetryPayload, EventPayload
from app.services.mqtt_service import publish_control_command
from app.repositories.models import Policy

async def get_active_policy():
    policy = await Policy.find_one(Policy.isActive == True)
    if not policy:
        # Default fallback
        policy = Policy(
            policyId="default",
            name="Default",
            helmetRequired=True,
            maxSpeedKph=25.0,
            sidewalkBrakeLevel=2
        )
    return policy

async def evaluate_telemetry_policy(data: TelemetryPayload):
    """
    Evaluate safety policies based on periodic telemetry data.
    """
    policy = await get_active_policy()
    
    # Rule B: Helmet is off while riding (or any time for now)
    if policy.helmetRequired and data.helmet and not data.helmet.worn:
        # Prevent riding
        await publish_control_command(
            device_id=data.deviceId,
            action="set_idle_mode",
            params={"brakeLevel": 3}, # Max brake or lock
            reason="Safety Policy: Helmet required but removed"
        )
        return

    # Additional telemetry-based rules can be added here
    if data.health and data.health.batteryPct < 5:
        await publish_control_command(
            device_id=data.deviceId,
            action="set_limit_mode",
            params={"targetSpeedKph": 5, "brakeLevel": 1},
            reason="Safety Policy: Critical battery level"
        )

async def evaluate_event_policy(data: EventPayload):
    """
    Evaluate safety policies based on critical events.
    """
    policy = await get_active_policy()
    
    # Rule A: Sidewalk detected with high confidence
    if data.eventType in ["sidewalk_detected", "auto_brake_triggered"]:
        if data.confidence >= 0.8:
            await publish_control_command(
                device_id=data.deviceId,
                action="set_limit_mode",
                params={"brakeLevel": policy.sidewalkBrakeLevel, "targetSpeedKph": 8},
                reason=f"Safety Policy: {data.eventType} (confidence: {data.confidence})"
            )
            return

    # Emergency Fall Detection
    if data.eventType == "fall_suspected" and data.severity == "high":
        # Immediate stop
        await publish_control_command(
            device_id=data.deviceId,
            action="set_idle_mode",
            params={"brakeLevel": 3, "siren": True},
            reason="Emergency: Fall suspected"
        )
