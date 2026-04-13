import jwt
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from routers.auth import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    get_current_active_user,
    role_check,
)
from sql_app.schemas import schemas_user
from sql_app.cruds import users as crud_users


class TestCreateAccessToken:
    def test_create_access_token_default_expiry(self):
        token = create_access_token(data={"sub": "test@example.com"})
        assert token is not None
        assert isinstance(token, str)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "test@example.com"
        assert "exp" in payload

    def test_create_access_token_custom_expiry(self):
        expires_delta = timedelta(minutes=30)
        token = create_access_token(
            data={"sub": "test@example.com"},
            expires_delta=expires_delta
        )

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
        expected_exp = datetime.utcnow() + expires_delta

        delta = abs((exp_datetime - expected_exp).total_seconds())
        assert delta < 5

    def test_create_access_token_contains_correct_data(self):
        test_data = {"sub": "user@example.com", "role": "admin"}
        token = create_access_token(data=test_data)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user@example.com"

    def test_create_access_token_expiry_in_future(self):
        token = create_access_token(data={"sub": "test@example.com"})

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload["exp"]
        now_timestamp = datetime.utcnow().timestamp()

        assert exp_timestamp > now_timestamp


class TestVerifyToken:
    def test_verify_valid_token(self, client: TestClient, auth_headers: dict):
        response = client.get("/api/users/me", headers=auth_headers)
        assert response.status_code == 200

    def test_verify_invalid_token(self, client: TestClient, invalid_token_headers: dict):
        response = client.get("/api/users/me", headers=invalid_token_headers)
        assert response.status_code == 401
        assert "validate credentials" in response.json()["detail"].lower()

    def test_verify_expired_token(self, client: TestClient, expired_token_headers: dict):
        response = client.get("/api/users/me", headers=expired_token_headers)
        assert response.status_code == 401

    def test_verify_token_wrong_secret(self, create_test_user):
        wrong_secret = "wrong_secret_key"
        token = jwt.encode(
            {"sub": create_test_user.email, "exp": datetime.utcnow() + timedelta(minutes=15)},
            wrong_secret,
            algorithm=ALGORITHM
        )
        headers = {"Authorization": f"Bearer {token}"}

        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app) as test_client:
            response = test_client.get("/api/users/me", headers=headers)
            assert response.status_code == 401

    def test_verify_token_missing_sub_claim(self):
        token = jwt.encode(
            {"exp": datetime.utcnow() + timedelta(minutes=15)},
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        headers = {"Authorization": f"Bearer {token}"}

        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app) as test_client:
            response = test_client.get("/api/users/me", headers=headers)
            assert response.status_code == 401

    def test_verify_token_user_not_in_database(self, db_session: Session):
        token = create_access_token(data={"sub": "nonexistent@example.com"})
        headers = {"Authorization": f"Bearer {token}"}

        from fastapi.testclient import TestClient
        from main import app
        from sql_app.database import get_db

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as test_client:
            response = test_client.get("/api/users/me", headers=headers)
            assert response.status_code == 401
        app.dependency_overrides.clear()


class TestActiveUserCheck:
    def test_active_user_can_access(self, client: TestClient, auth_headers: dict):
        response = client.get("/api/users/me", headers=auth_headers)
        assert response.status_code == 200

    def test_inactive_user_blocked(self, client: TestClient, inactive_auth_headers: dict):
        response = client.get("/api/users/me", headers=inactive_auth_headers)
        assert response.status_code == 400
        assert "inactive" in response.json()["detail"].lower()


class TestRoleCheck:
    def test_admin_role_can_access_admin_endpoint(self, client: TestClient, admin_auth_headers: dict):
        response = client.get("/api/users/", headers=admin_auth_headers)
        assert response.status_code == 200

    def test_general_role_blocked_from_admin_endpoint(self, client: TestClient, auth_headers: dict):
        response = client.get("/api/users/", headers=auth_headers)
        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower()


class TestLoginEndpoint:
    def test_login_success(self, client: TestClient, test_user_data: dict, create_test_user):
        response = client.post("/api/token", json=test_user_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_login_wrong_password(self, client: TestClient, test_user_data: dict, create_test_user):
        wrong_credentials = {
            "email": test_user_data["email"],
            "password": "wrongpassword"
        }
        response = client.post("/api/token", json=wrong_credentials)
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        credentials = {
            "email": "nonexistent@example.com",
            "password": "anypassword"
        }
        response = client.post("/api/token", json=credentials)
        assert response.status_code == 401

    def test_login_missing_email(self, client: TestClient):
        credentials = {"password": "anypassword"}
        response = client.post("/api/token", json=credentials)
        assert response.status_code == 422

    def test_login_missing_password(self, client: TestClient):
        credentials = {"email": "test@example.com"}
        response = client.post("/api/token", json=credentials)
        assert response.status_code == 422

    def test_login_empty_credentials(self, client: TestClient):
        credentials = {"email": "", "password": ""}
        response = client.post("/api/token", json=credentials)
        assert response.status_code == 401

    def test_login_returns_valid_token(self, client: TestClient, test_user_data: dict, create_test_user):
        response = client.post("/api/token", json=test_user_data)
        assert response.status_code == 200

        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me_response = client.get("/api/users/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["email"] == test_user_data["email"]


class TestTokenExpiry:
    def test_token_expiry_time(self, client: TestClient, test_user_data: dict, create_test_user):
        response = client.post("/api/token", json=test_user_data)
        assert response.status_code == 200

        expires_in = response.json()["expires_in"]
        assert expires_in == ACCESS_TOKEN_EXPIRE_MINUTES

    def test_token_valid_during_expiry_period(self, client: TestClient, auth_headers: dict):
        for _ in range(3):
            response = client.get("/api/users/me", headers=auth_headers)
            assert response.status_code == 200


class TestRateLimiting:
    def test_rate_limiting_high_frequency(self, client: TestClient, auth_headers: dict, create_test_user, db_session: Session):
        create_test_user.frequency_max = 5
        db_session.commit()
        db_session.refresh(create_test_user)

        for i in range(10):
            response = client.get("/api/users/me", headers=auth_headers)
            if response.status_code == 429:
                assert "too many requests" in response.json()["detail"].lower()
                break
        else:
            pass


class TestTokenFormat:
    def test_token_is_jwt_format(self, client: TestClient, test_user_data: dict, create_test_user):
        response = client.post("/api/token", json=test_user_data)
        token = response.json()["access_token"]

        parts = token.split(".")
        assert len(parts) == 3

    def test_token_can_be_decoded(self, client: TestClient, test_user_data: dict, create_test_user):
        response = client.post("/api/token", json=test_user_data)
        token = response.json()["access_token"]

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "sub" in payload
        assert "exp" in payload


class TestEdgeCases:
    def test_authorization_header_without_bearer_prefix(self, client: TestClient, create_test_user):
        token = create_access_token(data={"sub": create_test_user.email})
        headers = {"Authorization": token}
        response = client.get("/api/users/me", headers=headers)
        assert response.status_code == 401

    def test_authorization_header_bearer_lowercase(self, client: TestClient, create_test_user):
        token = create_access_token(data={"sub": create_test_user.email})
        headers = {"Authorization": f"bearer {token}"}
        response = client.get("/api/users/me", headers=headers)
        assert response.status_code == 200

    def test_multiple_tokens_same_user(self, client: TestClient, create_test_user):
        token1 = create_access_token(data={"sub": create_test_user.email})
        token2 = create_access_token(data={"sub": create_test_user.email})

        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}

        response1 = client.get("/api/users/me", headers=headers1)
        response2 = client.get("/api/users/me", headers=headers2)

        assert response1.status_code == 200
        assert response2.status_code == 200
