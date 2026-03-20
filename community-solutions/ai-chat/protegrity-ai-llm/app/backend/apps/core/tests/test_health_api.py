import pytest

@pytest.mark.django_db
def test_health_endpoint(client):
    response = client.get("/api/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
