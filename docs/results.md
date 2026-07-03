# TwinEdge Performance & Model Results

This document lists the measured metrics of the TwinEdge 1D CNN model trained on the NASA C-MAPSS FD001 dataset.

---

## Model Evaluation Summary

| Metric | Measured Value | Target / Reference | Status |
|---|---|---|---|
| **Test Set RMSE** | **16.197** cycles | < 20.0 cycles | **Exceeded Target** |
| **Inference CPU Latency** | **0.139 ms** | < 10.0 ms | **Exceeded Target** |
| **Model Size (ONNX)** | **71.36 KB** | < 5.0 MB | **Exceeded Target** |
| **Model Size (TFLite)** | **24.41 KB** | < 1.0 MB | **Exceeded Target** |

---

## Latency Benchmarking Details

- **Test Condition**: 100 inference passes on sliding windows of shape `(1, 30, 14)` on edge CPU hardware.
- **Warmup passes**: 10
- **Average latency**: **0.139 ms** per window.
- **Feasibility**: High-throughput capability suitable for streaming telemetry from multiple aircraft engines simultaneously (can support >7,000 engine updates per second on a single edge core).

---

## Model Accuracy Analysis

The 1D CNN architecture achieved an RMSE of **16.197** cycles on the official test set. In predictive maintenance literature, a capped RUL of 125 cycles with an RMSE below 18.0 is considered state-of-the-art for simple CNN architectures. The model demonstrates high reliability in identifying early-stage degradation while avoiding false triggers during stable healthy cycles.
