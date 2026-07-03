import requests
import json

def main():
    base_url = "http://localhost:8000"
    
    # 1. Test GET /telemetry/recent
    url_telemetry = f"{base_url}/telemetry/recent?engine_id=999"
    print(f"Testing GET {url_telemetry}...")
    try:
        res = requests.get(url_telemetry)
        print(f"Status Code: {res.status_code}")
        data = res.json()
        print(f"Returned {len(data)} telemetry records.")
        if len(data) > 0:
            print("Sample record:", data[0])
    except Exception as e:
        print(f"Failed to query telemetry: {e}")

    # 2. Add a mock alert to DB to test alert endpoints
    from app.db import add_alert, get_unresolved_alerts
    print("Inserting a mock alert 'test_alert_123' directly into DB...")
    add_alert(
        alert_id="test_alert_123",
        engine_id=1,
        cycle=150,
        rul_prediction=45.2,
        anomaly_flag=1
    )
    
    # 3. Test GET /alerts
    url_alerts = f"{base_url}/alerts"
    print(f"Testing GET {url_alerts}...")
    try:
        res = requests.get(url_alerts)
        print(f"Status: {res.status_code}")
        alerts = res.json()
        print(f"Returned {len(alerts)} unresolved alerts.")
        print("Alerts list:", alerts)
        
        # Verify our alert is in the list
        assert any(a['id'] == 'test_alert_123' for a in alerts)
    except Exception as e:
        print(f"Failed to query alerts: {e}")
        
    # 4. Test POST /alerts/{id}/signoff
    url_signoff = f"{base_url}/alerts/test_alert_123/signoff"
    print(f"Testing POST {url_signoff}...")
    payload = {
        "status": "APPROVED",
        "notes": "Verified high temperature and vibration. Scheduled sensor replacement."
    }
    try:
        res = requests.post(url_signoff, json=payload)
        print(f"Status: {res.status_code}")
        print("Response:", res.json())
        
        # Verify it is no longer in unresolved alerts
        res_check = requests.get(url_alerts)
        alerts_check = res_check.json()
        assert not any(a['id'] == 'test_alert_123' for a in alerts_check)
        print("Successfully verified alert is resolved and removed from queue.")
        
        # Check in all alerts (audit log)
        res_all = requests.get(f"{url_alerts}?unresolved_only=false")
        all_alerts = res_all.json()
        matching = [a for a in all_alerts if a['id'] == 'test_alert_123']
        assert len(matching) == 1
        assert matching[0]['status'] == 'APPROVED'
        assert matching[0]['notes'] == 'Verified high temperature and vibration. Scheduled sensor replacement.'
        print("Audit log verification passed!")
        print("ACCEPTANCE CHECK: PASS")
    except Exception as e:
        print(f"Signoff endpoint test failed: {e}")

if __name__ == "__main__":
    main()
