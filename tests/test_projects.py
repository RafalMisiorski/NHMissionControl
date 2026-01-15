"""Project API tests"""


def test_list_projects_empty(client):
    """Test listing projects when empty"""
    response = client.get("/api/v1/projects/")
    assert response.status_code == 200
    assert response.json() == []


def test_create_project(client):
    """Test creating a project"""
    project_data = {
        "name": "Test Project",
        "description": "A test project",
        "status": "active"
    }
    response = client.post("/api/v1/projects/", json=project_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == project_data["name"]
    assert data["description"] == project_data["description"]
    assert data["status"] == project_data["status"]
    assert "id" in data
    assert "created_at" in data


def test_get_project(client):
    """Test getting a specific project"""
    # Create a project first
    project_data = {"name": "Test Project", "status": "active"}
    create_response = client.post("/api/v1/projects/", json=project_data)
    project_id = create_response.json()["id"]

    # Get the project
    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["name"] == project_data["name"]


def test_get_project_not_found(client):
    """Test getting a non-existent project"""
    response = client.get("/api/v1/projects/999")
    assert response.status_code == 404


def test_update_project(client):
    """Test updating a project"""
    # Create a project
    create_response = client.post(
        "/api/v1/projects/",
        json={"name": "Original", "status": "active"}
    )
    project_id = create_response.json()["id"]

    # Update it
    response = client.put(
        f"/api/v1/projects/{project_id}",
        json={"name": "Updated", "status": "completed"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"
    assert response.json()["status"] == "completed"


def test_delete_project(client):
    """Test deleting a project"""
    # Create a project
    create_response = client.post(
        "/api/v1/projects/",
        json={"name": "To Delete", "status": "active"}
    )
    project_id = create_response.json()["id"]

    # Delete it
    response = client.delete(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200

    # Verify it's gone
    get_response = client.get(f"/api/v1/projects/{project_id}")
    assert get_response.status_code == 404
