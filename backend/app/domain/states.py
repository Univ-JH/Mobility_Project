from enum import Enum
from typing import List

class DeviceState(str, Enum):
    IDLE = "IDLE"
    READY = "READY"
    RUNNING_NORMAL = "RUNNING_NORMAL"
    RUNNING_LIMITED = "RUNNING_LIMITED"
    AUTO_BRAKING = "AUTO_BRAKING"
    EMERGENCY = "EMERGENCY"
    FAULT = "FAULT"

class EmergencyStatus(str, Enum):
    OPEN = "open"
    ACKED = "acked"
    RESOLVED = "resolved"
    FALSE_ALARM = "false_alarm"

# State Transition Matrix
# from_state: [allowed_to_states]
ALLOWED_TRANSITIONS = {
    DeviceState.IDLE: [DeviceState.READY, DeviceState.FAULT],
    DeviceState.READY: [DeviceState.RUNNING_NORMAL, DeviceState.IDLE, DeviceState.FAULT],
    DeviceState.RUNNING_NORMAL: [DeviceState.RUNNING_LIMITED, DeviceState.AUTO_BRAKING, DeviceState.IDLE, DeviceState.FAULT],
    DeviceState.RUNNING_LIMITED: [DeviceState.AUTO_BRAKING, DeviceState.RUNNING_NORMAL, DeviceState.IDLE, DeviceState.FAULT],
    DeviceState.AUTO_BRAKING: [DeviceState.EMERGENCY, DeviceState.RUNNING_LIMITED, DeviceState.IDLE, DeviceState.FAULT],
    DeviceState.EMERGENCY: [DeviceState.IDLE, DeviceState.FAULT],
    DeviceState.FAULT: [DeviceState.IDLE]
}

def is_transition_allowed(from_state: DeviceState, to_state: DeviceState) -> bool:
    """Check if state transition is valid based on ALLOWED_TRANSITIONS."""
    if from_state == to_state:
        return True # Self transition is usually fine or ignored
    return to_state in ALLOWED_TRANSITIONS.get(from_state, [])
