import os
import time
import json
import requests
import pandas as pd
import paho.mqtt.client as mqtt
from datetime import datetime

BACKEND_URL = "http://localhost:8000"
MQTT_HOST = "localhost"
MQTT_PORT = 1883

def get_mqtt_client():
    client = mqtt.Client()
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        return client
    except Exception as e:
        print(f"Failed to connect to MQTT broker: {e}")
        return None

def main():
    print("Starting TwinEdge Telemetry Simulator...")
    
    # 1. Load test data
    raw_dir = "/home/saran/project/TwinEdge/backend/data/raw"
    test_path = os.path.join(raw_dir, 'test_FD001.txt')
    
    if not os.path.exists(test_path):
        print(f"Error: {test_path} not found. Please run preprocessing first.")
        return
        
    index_names = ['unit_number', 'time_in_cycles']
    setting_names = ['setting_1', 'setting_2', 'setting_3']
    sensor_names = [f's_{i}' for i in range(1, 22)]
    col_names = index_names + setting_names + sensor_names
    
    test_df = pd.read_csv(test_path, sep=r'\s+', header=None, names=col_names)
    
    # Standard C-MAPSS: Drop near-zero variance sensors and setting columns
    sensors_to_drop = ['s_1', 's_5', 's_6', 's_10', 's_16', 's_18', 's_19']
    feature_cols = [s for s in sensor_names if s not in sensors_to_drop]
    
    # Filter engine 1 to simulate a live run
    engine_id = 1
    engine_df = test_df[test_df['unit_number'] == engine_id].sort_values('time_in_cycles')
    print(f"Loaded {len(engine_df)} cycles of telemetry for Engine #{engine_id}.")

    # Establish MQTT connection
    mqtt_client = get_mqtt_client()
    if not mqtt_client:
        print("Continuing without MQTT (results won't be logged to InfluxDB).")

    # Start simulation loop
    # In CMAPSS, all engines start in healthy state and degrade over time.
    # To run a fast demo, we start at cycle 1 and stream up to the last cycle.
    # We need at least 30 cycles to form the first sliding window!
    print("Streaming telemetry cycle-by-cycle (0.5 seconds per cycle)...")
    
    for cycle in range(30, len(engine_df) + 1):
        window_df = engine_df.iloc[cycle-30:cycle]
        raw_window = window_df[feature_cols].values.tolist()
        current_cycle = int(engine_df.iloc[cycle-1]['time_in_cycles'])
        
        # 1. Post to local edge backend for inference (RUL + Anomaly flag)
        payload = {
            "engine_id": engine_id,
            "cycle": current_cycle,
            "window": raw_window
        }
        
        rul_prediction = 125.0
        anomaly_flag = 0
        confidence = 0.8
        
        try:
            res = requests.post(f"{BACKEND_URL}/predict", json=payload, timeout=2)
            if res.ok:
                data = res.json()
                rul_prediction = data["rul_prediction"]
                anomaly_flag = data["anomaly_flag"]
                confidence = data["confidence"]
                print(f"[Cycle {current_cycle:3d}] Prediction: RUL = {rul_prediction:5.1f} cycles | Anomaly = {anomaly_flag} (Confidence: {confidence:.2f})")
            else:
                print(f"[Cycle {current_cycle:3d}] Inference Error: Backend returned status {res.status_code}")
        except Exception as e:
            print(f"[Cycle {current_cycle:3d}] Backend Unreachable. Using fallback model...")
            # Fallback estimation if backend is offline (resilience demo beat)
            # RUL decreases linearly in failure mode, let's estimate
            rul_prediction = max(0.0, 125.0 - (current_cycle - 30) * 1.5)
            anomaly_flag = int(rul_prediction < 60)
            confidence = 0.5
            
        # 2. Publish the full telemetry packet via MQTT
        if mqtt_client:
            # We map sensor values of the current cycle (last row of window)
            current_sensors = window_df[feature_cols].iloc[-1].tolist()
            mqtt_payload = {
                "engine_id": engine_id,
                "cycle": current_cycle,
                "sensors": current_sensors,
                "rul_prediction": rul_prediction,
                "anomaly_flag": anomaly_flag,
                "timestamp": datetime.utcnow().isoformat()
            }
            try:
                mqtt_client.publish("twinedge/telemetry", json.dumps(mqtt_payload))
            except Exception as e:
                print(f"MQTT publish error: {e}")
                
        time.sleep(0.5)

    if mqtt_client:
        mqtt_client.disconnect()
    print("Simulation stream complete.")

if __name__ == "__main__":
    main()
