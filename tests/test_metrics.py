"""Metrics API tests"""


def test_list_metrics_empty(client):
    """Test listing metrics when empty"""
    response = client.get("/api/v1/metrics/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_metric(client):
    """Test creating a metric"""
    metric_data = {
        "name": "cpu_usage",
        "value": 75.5,
        "unit": "percent"
    }
    response = client.post("/api/v1/metrics/", json=metric_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == metric_data["name"]
    assert data["value"] == metric_data["value"]
    assert data["unit"] == metric_data["unit"]
    assert "id" in data


def test_get_metric(client):
    """Test getting a specific metric"""
    # Create a metric first
    create_response = client.post("/api/v1/metrics/", json={
        "name": "memory_usage",
        "value": 60.0,
        "unit": "percent"
    })
    metric_id = create_response.json()["id"]

    # Get the metric
    response = client.get(f"/api/v1/metrics/{metric_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "memory_usage"


def test_get_metrics_summary(client):
    """Test getting metrics summary"""
    # Create some metrics
    client.post("/api/v1/metrics/", json={
        "name": "metric1",
        "value": 100.0
    })
    client.post("/api/v1/metrics/", json={
        "name": "metric2",
        "value": 200.0
    })

    response = client.get("/api/v1/metrics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_metrics"] == 2
    assert data["avg_value"] == 150.0


def test_delete_metric(client):
    """Test deleting a metric"""
    # Create a metric
    create_response = client.post("/api/v1/metrics/", json={
        "name": "to_delete",
        "value": 50.0
    })
    metric_id = create_response.json()["id"]

    # Delete it
    response = client.delete(f"/api/v1/metrics/{metric_id}")
    assert response.status_code == 200

    # Verify it's gone
    get_response = client.get(f"/api/v1/metrics/{metric_id}")
    assert get_response.status_code == 404


def test_filter_metrics_by_project(client):
    """Test filtering metrics by project"""
    # First create a project
    project_response = client.post("/api/v1/projects/", json={
        "name": "Test Project",
        "status": "active"
    })
    project_id = project_response.json()["id"]

    # Create metrics with and without project
    client.post("/api/v1/metrics/", json={
        "name": "with_project",
        "value": 100.0,
        "project_id": project_id
    })
    client.post("/api/v1/metrics/", json={
        "name": "without_project",
        "value": 200.0
    })

    # Filter by project
    response = client.get(f"/api/v1/metrics/?project_id={project_id}")
    assert response.status_code == 200
    metrics = response.json()
    assert len(metrics) == 1
    assert metrics[0]["name"] == "with_project"
