import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import add_alert, init_db

# Initialize database for testing
init_db()

def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

def test_predict_validation():
    # Test invalid window shape
    payload = {
        "engine_id": 1,
        "cycle": 1,
        "window": [[1.0] * 14] * 20 # Only 20 cycles instead of 30
    }
    with TestClient(app) as client:
        response = client.post("/predict", json=payload)
        assert response.status_code == 400
        assert "Expected window shape (30, 14)" in response.json()["detail"]

def test_alerts_signoff():
    # Insert mock alert directly to database
    add_alert("test_pytest_123", 1, 100, 50.0, 1)
    
    with TestClient(app) as client:
        # Verify it shows up in GET /alerts
        response = client.get("/alerts")
        assert response.status_code == 200
        alerts = response.json()
        assert any(a["id"] == "test_pytest_123" for a in alerts)
        
        # Sign off the alert
        signoff_payload = {
            "status": "APPROVED",
            "notes": "Pytest verification notes"
        }
        signoff_response = client.post("/alerts/test_pytest_123/signoff", json=signoff_payload)
        assert signoff_response.status_code == 200
        assert signoff_response.json()["status"] == "success"
        
        # Verify it is no longer in unresolved queue
        response = client.get("/alerts")
        assert response.status_code == 200
        alerts = response.json()
        assert not any(a["id"] == "test_pytest_123" for a in alerts)
