def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["checks"]["api"] is True
    assert payload["checks"]["database"] is True
    assert payload["checks"]["minio"] is True
