import asyncio
import aiomqtt
import json
from app.core.config import settings
from app.workers.ingestion_worker import handle_mqtt_message

async def start_mqtt_worker():
    """
    Connects to the MQTT broker and subscribes to v1 topics.
    Maintains auto-reconnection loop.
    """
    reconnect_interval = 5

    while True:
        try:
            # We use context manager for automatic connection tearing down and keepalives
            async with aiomqtt.Client(
                hostname=settings.MQTT_BROKER_URL,
                port=settings.MQTT_PORT,
                client_id=settings.MQTT_CLIENT_ID
            ) as client:
                print(f"Connected to MQTT broker at {settings.MQTT_BROKER_URL}:{settings.MQTT_PORT}")
                
                # Subscribe to required topics
                await client.subscribe("device/+/telemetry")
                await client.subscribe("device/+/event")
                
                async for message in client.messages:
                    topic = str(message.topic)
                    payload_bytes = message.payload
                    
                    try:
                        payload_dict = json.loads(payload_bytes.decode('utf-8'))
                        # Spawn background task to handle message asynchronously to prevent blocking the MQTT receiver loop
                        asyncio.create_task(handle_mqtt_message(topic, payload_dict))
                    except json.JSONDecodeError:
                        print(f"Failed to decode JSON from topic: {topic}")
                        
        except aiomqtt.MqttError as error:
            print(f"MQTT Error: {error}. Reconnecting in {reconnect_interval} seconds...")
            await asyncio.sleep(reconnect_interval)
        except Exception as error:
            print(f"MQTT Worker unexpected error: {type(error).__name__}: {error}. Reconnecting in {reconnect_interval} seconds...")
            await asyncio.sleep(reconnect_interval)
