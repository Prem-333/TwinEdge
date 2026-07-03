import os
import json
import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

client = mqtt.Client()

def get_mqtt_client():
    if not client.is_connected():
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            client.loop_start()
            print(f"Connected to MQTT broker at {MQTT_HOST}:{MQTT_PORT}")
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
    return client

def publish_telemetry(engine_id: int, cycle: int, sensor_values: list, rul_prediction: float, anomaly_flag: int):
    mqtt_client = get_mqtt_client()
    if not mqtt_client.is_connected():
        print("MQTT client not connected. Skipping publish.")
        return False
        
    payload = {
        "engine_id": engine_id,
        "cycle": cycle,
        "sensors": sensor_values,
        "rul_prediction": rul_prediction,
        "anomaly_flag": anomaly_flag,
        "timestamp": datetime_str()
    }
    
    # Publish to telemetry topic
    mqtt_client.publish("twinedge/telemetry", json.dumps(payload))
    
    # If anomaly, also publish to alerts topic
    if anomaly_flag:
        alert_payload = {
            "alert_id": f"alert_engine_{engine_id}_cycle_{cycle}",
            "engine_id": engine_id,
            "cycle": cycle,
            "rul_prediction": rul_prediction,
            "timestamp": datetime_str(),
            "description": f"Engine {engine_id} degradation flagged: RUL {rul_prediction} cycles remaining."
        }
        mqtt_client.publish("twinedge/alerts", json.dumps(alert_payload))
        
    return True

def datetime_str():
    from datetime import datetime
    return datetime.utcnow().isoformat()
