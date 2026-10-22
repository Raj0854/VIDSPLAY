def test_admin_login_success(client):
    res = client.post("/api/auth/login", json={
        "username": "testadmin",
        "password": "admin123"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["username"] == "testadmin"


def test_admin_login_invalid_password(client):
    res = client.post("/api/auth/login", json={
        "username": "testadmin",
        "password": "wrongpassword"
    })
    assert res.status_code == 401
    data = res.get_json()
    assert data["success"] is False


def test_admin_me_endpoint(auth_client):
    res = auth_client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.get_json()
    assert data["authenticated"] is True
    assert data["user"]["username"] == "testadmin"


def test_admin_logout(auth_client):
    res = auth_client.post("/api/auth/logout")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True

    # Check that me is now unauthenticated
    me_res = auth_client.get("/api/auth/me")
    assert me_res.get_json()["authenticated"] is False


def test_protected_route_requires_auth(client):
    # Unauthenticated user trying to access admin dashboard endpoint
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 401
