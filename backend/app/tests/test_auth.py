def test_login_success_and_me(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123456"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert "documents:write" in payload["user"]["permissions"]

    me = client.get("/api/me", headers={"Authorization": f"Bearer {payload['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == "admin"


def test_login_failure(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "bad"})
    assert response.status_code == 401
