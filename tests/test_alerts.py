"""Alert API tests"""


def test_list_alerts_empty(client):
    """Test listing alerts when empty"""
    response = client.get("/api/v1/alerts/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_alert(client):
    """Test creating an alert"""
    alert_data = {
        "title": "Test Alert",
        "message": "This is a test alert",
        "severity": "warning",
        "source": "test-system"
    }
    response = client.post("/api/v1/alerts/", json=alert_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == alert_data["title"]
    assert data["message"] == alert_data["message"]
    assert data["severity"] == alert_data["severity"]
    assert data["acknowledged"] == False
    assert "id" in data


def test_get_active_alerts(client):
    """Test getting active (unacknowledged) alerts"""
    # Create two alerts
    client.post("/api/v1/alerts/", json={
        "title": "Alert 1",
        "message": "First alert",
        "severity": "info"
    })
    client.post("/api/v1/alerts/", json={
        "title": "Alert 2",
        "message": "Second alert",
        "severity": "error"
    })

    response = client.get("/api/v1/alerts/active")
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) == 2
    assert all(not a["acknowledged"] for a in alerts)


def test_acknowledge_alert(client):
    """Test acknowledging an alert"""
    # Create an alert
    create_response = client.post("/api/v1/alerts/", json={
        "title": "Test Alert",
        "message": "To be acknowledged",
        "severity": "warning"
    })
    alert_id = create_response.json()["id"]

    # Acknowledge it
    response = client.put(f"/api/v1/alerts/{alert_id}/acknowledge")
    assert response.status_code == 200
    data = response.json()
    assert data["acknowledged"] == True
    assert data["acknowledged_at"] is not None


def test_filter_alerts_by_severity(client):
    """Test filtering alerts by severity"""
    # Create alerts with different severities
    client.post("/api/v1/alerts/", json={
        "title": "Info Alert",
        "message": "Info level",
        "severity": "info"
    })
    client.post("/api/v1/alerts/", json={
        "title": "Critical Alert",
        "message": "Critical level",
        "severity": "critical"
    })

    # Filter by severity
    response = client.get("/api/v1/alerts/?severity=critical")
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "critical"


def test_delete_alert(client):
    """Test deleting an alert"""
    # Create an alert
    create_response = client.post("/api/v1/alerts/", json={
        "title": "To Delete",
        "message": "Will be deleted",
        "severity": "info"
    })
    alert_id = create_response.json()["id"]

    # Delete it
    response = client.delete(f"/api/v1/alerts/{alert_id}")
    assert response.status_code == 200

    # Verify it's gone
    get_response = client.get(f"/api/v1/alerts/{alert_id}")
    assert get_response.status_code == 404
