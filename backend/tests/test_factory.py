def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["status"] == "healthy"
    assert "version" in json_data
    assert json_data["services"]["mongodb"] == "connected"

def test_indexes_initialized(db):
    # Verify that key collections have indexes initialized
    users_info = db.users.index_information()
    assert "email_1" in users_info
    assert users_info["email_1"]["unique"] is True

    sessions_info = db.sessions.index_information()
    assert "expires_at_1" in sessions_info
    assert "expireAfterSeconds" in sessions_info["expires_at_1"]

    organisations_info = db.organisations.index_information()
    assert "slug_1" in organisations_info
    assert organisations_info["slug_1"]["unique"] is True
