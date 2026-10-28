def registration_payload():
    return {
        "name": "Test User",
        "email": "test@example.com",
        "password": "Password123!",
    }


class TestRegisterUser:
    """Tests for POST /auth/register"""

    def test_register_user_success(self, client):
        response = client.post("/auth/register", json=registration_payload())

        assert response.status_code == 201
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]

    def test_register_user_missing_name(self, client):
        payload = registration_payload()
        payload.pop("name")

        response = client.post("/auth/register", json=payload)

        assert response.status_code == 422
        assert response.json()["detail"][0]["type"] == "missing"
        assert response.json()["detail"][0]["loc"] == ["body", "name"]

    def test_register_user_short_password(self, client):
        payload = registration_payload()
        payload["password"] = "short"

        response = client.post("/auth/register", json=payload)

        assert response.status_code == 422

    def test_register_duplicate_email(self, client):
        payload = registration_payload()
        first_response = client.post("/auth/register", json=payload)
        duplicate_response = client.post("/auth/register", json=payload)

        assert first_response.status_code == 201
        assert duplicate_response.status_code == 409
        assert duplicate_response.json() == {
            "detail": f"User with email '{payload['email']}' already exists"
        }


class TestLoginUser:
    """Tests for POST /auth/login."""

    def test_login_user_success(self, client):
        payload = registration_payload()
        client.post("/auth/register", json=payload)

        response = client.post(
            "/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )

        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"
        assert response.json()["access_token"]

    def test_login_user_invalid_password(self, client):
        payload = registration_payload()
        client.post("/auth/register", json=payload)

        response = client.post(
            "/auth/login",
            json={"email": payload["email"], "password": "WrongPassword123!"},
        )

        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid email or password"}


class TestCurrentUser:
    """Tests for the protected GET /users/me endpoint."""

    def test_current_user_requires_authentication(self, client):
        response = client.get("/users/me")

        assert response.status_code == 401

    def test_current_user_profile_excludes_password(self, client):
        payload = registration_payload()
        register_response = client.post("/auth/register", json=payload)
        token = register_response.json()["access_token"]

        response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == payload["name"]
        assert response.json()["email"] == payload["email"]
        assert "hashed_password" not in response.json()
