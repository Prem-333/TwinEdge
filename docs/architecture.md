# TwinEdge Architecture: Real vs Mocked Scope

This document details the actual design implementation of the TwinEdge digital twin MRO prototype, outlining the engineering tradeoffs made during the prototype build.

---

## Technical Architecture

TwinEdge is designed as a fully localized edge deployment for UDAN aircraft hangars.

```
   [ C-MAPSS Sensor Data ]
             |
             v
     [ 1D CNN Inference ]   <-- Local ONNX Model (twinedge_rul.onnx)
             |
             v (Publish telemetry + anomaly)
      [ MQTT Broker ]       <-- Eclipse Mosquitto (twinedge_mosquitto)
             |
             v (Subscribe)
     [ Subscriber Loop ]    <-- influx_writer.py (runs in twinedge_subscriber)
             |
             +---> [ InfluxDB Local Cache ] (If online)
             |
             +---> [ SQLite Local Buffer ]  (If InfluxDB unreachable)
                     |
                     v (Auto-flush on reconnect)
                     InfluxDB
```

---

## Implementation Realism: Real vs Mocked

To build a high-credibility demo under hackathon timelines, we made specific scoping choices:

### 1. What is 100% Real
* **Edge Inference Model**: A real 1D CNN model trained on NASA C-MAPSS FD001 dataset run-to-failure trajectories. The model is exported to a quantized `.onnx` and `.tflite` format and loaded at runtime in FastAPI using `onnxruntime`.
* **Telemetry Preprocessing**: Standard scaling and sliding window conversion (size 30) are fitted exclusively on the training set and saved to `scaler.joblib` to prevent data leakage.
* **Offline Resilience Layer**: The SQLite database fallback mechanism is fully implemented. If InfluxDB shuts down, incoming MQTT records are written to a local buffer table. On reconnect, the subscriber flushes the records in chronological order to InfluxDB.
* **FastAPI Backend & DB**: Local sqlite3 storage tracks unresolved AME alerts and persists engineer sign-offs (approved/rejected/escalated decisions) alongside notes to act as a tamper-proof audit log.
* **MQTT Telemetry Pipeline**: Real eclipse-mosquitto broker routing messages from a Python streaming generator (`simulator.py`) to the InfluxDB writer.

### 2. What is Simplified/Mocked
* **K3s Orchestration (Simplified)**: While the production design specifies K3s/Kubernetes for managing edge nodes, the hackathon prototype runs on a optimized `docker` container layout using `run_infra.sh`.
* **LLM Diagnostics (Mocked)**: The LLM diagnostic report panel in the React frontend uses a local templates lookup. The UI clearly labels this as `Llama-3-Edge-8B [DEMO OFFLINE MOCK]`. It is not calling a live inference API to remain fully functional offline.
* **Cloud Sync (Omitted)**: Telemetry is cached locally in InfluxDB. Synchronization to a cloud dashboard is planned but not implemented in this prototype stage.
