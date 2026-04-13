import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from sql_app import models
from sql_app.cruds import users as crud_users
from sql_app.schemas import schemas_user
from tests.conftest import override_dependency
from routers.auth import get_current_user, get_current_active_user, role_check


class TestCreateUser:
    def test_create_user_success(self, client: TestClient, test_user_data: dict):
        response = client.post("/api/users/", json=test_user_data)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert "id" in data
        assert data["role"] == "general"

    def test_create_user_duplicate_email(self, client: TestClient, create_test_user, test_user_data: dict):
        response = client.post("/api/users/", json=test_user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_create_user_invalid_email(self, client: TestClient):
        response = client.post("/api/users/", json={
            "email": "invalid-email",
            "password": "password123"
        })
        assert response.status_code == 200

    def test_create_user_missing_password(self, client: TestClient):
        response = client.post("/api/users/", json={"email": "test@example.com"})
        assert response.status_code == 422

    def test_create_user_missing_email(self, client: TestClient):
        response = client.post("/api/users/", json={"password": "password123"})
        assert response.status_code == 422

    def test_create_user_empty_body(self, client: TestClient):
        response = client.post("/api/users/", json={})
        assert response.status_code == 422

    def test_create_user_very_long_username(self, client: TestClient):
        long_email = "a" * 200 + "@example.com"
        response = client.post("/api/users/", json={
            "email": long_email,
            "password": "password123"
        })
        assert response.status_code == 200


class TestReadUsers:
    def test_read_users_as_admin(self, client: TestClient, admin_auth_headers: dict, create_test_user):
        response = client.get("/api/users/", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_read_users_as_general_user_denied(self, client: TestClient, auth_headers: dict):
        response = client.get("/api/users/", headers=auth_headers)
        assert response.status_code == 403

    def test_read_users_unauthorized(self, client: TestClient):
        response = client.get("/api/users/")
        assert response.status_code == 401

    def test_read_users_pagination(self, client: TestClient, admin_auth_headers: dict, db_session: Session):
        for i in range(15):
            user_create = schemas_user.UserCreate(
                email=f"user{i}@example.com",
                password="password123"
            )
            crud_users.create_user(db_session, user_create)

        response = client.get("/api/users/?skip=5&limit=5", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_read_users_empty_database(self, client: TestClient, db_session: Session):
        from main import app
        from sql_app.database import get_db

        admin_user = models.User(
            email="admin@test.com",
            username="admin",
            hashed_password="hash",
            role="admin",
            is_active=True
        )
        db_session.add(admin_user)
        db_session.commit()
        db_session.refresh(admin_user)

        def override_get_current_user():
            return admin_user

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_current_user] = override_get_current_user
        app.dependency_overrides[get_current_active_user] = override_get_current_user
        app.dependency_overrides[role_check] = override_get_current_user
        app.dependency_overrides[get_db] = override_get_db

        from fastapi.testclient import TestClient
        with TestClient(app) as test_client:
            response = test_client.get("/api/users/")
            assert response.status_code == 200
            assert len(response.json()) == 1

        app.dependency_overrides.clear()


class TestReadUserMe:
    def test_read_user_me_success(self, client: TestClient, auth_headers: dict, create_test_user):
        response = client.get("/api/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == create_test_user.email
        assert data["id"] == create_test_user.id

    def test_read_user_me_unauthorized(self, client: TestClient):
        response = client.get("/api/users/me")
        assert response.status_code == 401

    def test_read_user_me_inactive_user(self, client: TestClient, inactive_auth_headers: dict):
        response = client.get("/api/users/me", headers=inactive_auth_headers)
        assert response.status_code == 400
        assert "inactive" in response.json()["detail"].lower()


class TestReadUserById:
    def test_read_user_by_id_own_user(self, client: TestClient, auth_headers: dict, create_test_user):
        response = client.get(f"/api/users/{create_test_user.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == create_test_user.id

    def test_read_user_by_id_admin_can_read_other(self, client: TestClient, admin_auth_headers: dict, create_test_user):
        response = client.get(f"/api/users/{create_test_user.id}", headers=admin_auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == create_test_user.id

    def test_read_user_by_id_general_user_cannot_read_other(self, client: TestClient, auth_headers: dict, create_test_admin):
        response = client.get(f"/api/users/{create_test_admin.id}", headers=auth_headers)
        assert response.status_code == 403

    def test_read_user_by_id_not_found(self, client: TestClient, admin_auth_headers: dict):
        response = client.get("/api/users/99999", headers=admin_auth_headers)
        assert response.status_code == 404

    def test_read_user_by_id_unauthorized(self, client: TestClient, create_test_user):
        response = client.get(f"/api/users/{create_test_user.id}")
        assert response.status_code == 401

    def test_read_user_by_id_negative_id(self, client: TestClient, admin_auth_headers: dict):
        response = client.get("/api/users/-1", headers=admin_auth_headers)
        assert response.status_code == 404

    def test_read_user_by_id_zero(self, client: TestClient, admin_auth_headers: dict):
        response = client.get("/api/users/0", headers=admin_auth_headers)
        assert response.status_code == 404


class TestDeleteUser:
    def test_delete_user_own_account(self, client: TestClient, auth_headers: dict, create_test_user):
        response = client.delete(f"/api/users/{create_test_user.id}", headers=auth_headers)
        assert response.status_code == 200
        assert "deleted" in response.json()["msg"].lower()

    def test_delete_user_admin_can_delete_other(self, client: TestClient, admin_auth_headers: dict, create_test_user):
        response = client.delete(f"/api/users/{create_test_user.id}", headers=admin_auth_headers)
        assert response.status_code == 200

    def test_delete_user_general_cannot_delete_other(self, client: TestClient, auth_headers: dict, create_test_admin):
        response = client.delete(f"/api/users/{create_test_admin.id}", headers=auth_headers)
        assert response.status_code == 403

    def test_delete_user_not_found(self, client: TestClient, admin_auth_headers: dict):
        response = client.delete("/api/users/99999", headers=admin_auth_headers)
        assert response.status_code == 404

    def test_delete_user_unauthorized(self, client: TestClient, create_test_user):
        response = client.delete(f"/api/users/{create_test_user.id}")
        assert response.status_code == 401

    def test_delete_user_twice(self, client: TestClient, admin_auth_headers: dict, create_test_user):
        response1 = client.delete(f"/api/users/{create_test_user.id}", headers=admin_auth_headers)
        assert response1.status_code == 200

        response2 = client.delete(f"/api/users/{create_test_user.id}", headers=admin_auth_headers)
        assert response2.status_code == 404


class TestUpdateUser:
    def test_update_user_own_account(self, client: TestClient, auth_headers: dict, create_test_user):
        update_data = {
            "id": create_test_user.id,
            "email": create_test_user.email,
            "username": "newusername",
            "avatar": "https://example.com/newavatar.png",
            "role": "general",
            "is_active": True,
            "frequency_max": 600
        }
        response = client.put("/api/users/", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        assert "updated" in response.json()["msg"].lower()

    def test_update_user_admin_can_update_other(self, client: TestClient, admin_auth_headers: dict, create_test_user):
        update_data = {
            "id": create_test_user.id,
            "email": create_test_user.email,
            "username": "adminupdated",
            "avatar": None,
            "role": "admin",
            "is_active": True,
            "frequency_max": 800
        }
        response = client.put("/api/users/", json=update_data, headers=admin_auth_headers)
        assert response.status_code == 200

    def test_update_user_general_cannot_update_other(self, client: TestClient, auth_headers: dict, create_test_admin):
        update_data = {
            "id": create_test_admin.id,
            "email": create_test_admin.email,
            "username": "hackattempt",
            "avatar": None,
            "role": "general",
            "is_active": True,
            "frequency_max": 600
        }
        response = client.put("/api/users/", json=update_data, headers=auth_headers)
        assert response.status_code == 403

    def test_update_user_general_cannot_change_role(self, client: TestClient, auth_headers: dict, create_test_user):
        update_data = {
            "id": create_test_user.id,
            "email": create_test_user.email,
            "username": create_test_user.username,
            "avatar": None,
            "role": "admin",
            "is_active": True,
            "frequency_max": 600
        }
        response = client.put("/api/users/", json=update_data, headers=auth_headers)
        assert response.status_code == 200

        verify_response = client.get(f"/api/users/{create_test_user.id}", headers=auth_headers)
        assert verify_response.json()["role"] == "general"

    def test_update_user_not_found(self, client: TestClient, admin_auth_headers: dict):
        update_data = {
            "id": 99999,
            "email": "notfound@example.com",
            "username": "notfound",
            "avatar": None,
            "role": "general",
            "is_active": True,
            "frequency_max": 600
        }
        response = client.put("/api/users/", json=update_data, headers=admin_auth_headers)
        assert response.status_code == 404

    def test_update_user_unauthorized(self, client: TestClient, create_test_user):
        update_data = {
            "id": create_test_user.id,
            "email": create_test_user.email,
            "username": "unauthorized",
            "avatar": None,
            "role": "general",
            "is_active": True,
            "frequency_max": 600
        }
        response = client.put("/api/users/", json=update_data)
        assert response.status_code == 401


class TestUpdateUserPassword:
    def test_update_password_success(self, client: TestClient, auth_headers: dict, create_test_user, test_user_data: dict):
        password_data = {
            "id": create_test_user.id,
            "oldpassword": test_user_data["password"],
            "password": "newpassword123"
        }
        response = client.post("/api/users/password/", json=password_data, headers=auth_headers)
        assert response.status_code == 200

    def test_update_password_wrong_old_password(self, client: TestClient, auth_headers: dict, create_test_user):
        password_data = {
            "id": create_test_user.id,
            "oldpassword": "wrongoldpassword",
            "password": "newpassword123"
        }
        response = client.post("/api/users/password/", json=password_data, headers=auth_headers)
        assert response.status_code == 403

    def test_update_password_cannot_change_other_user(self, client: TestClient, auth_headers: dict, create_test_admin):
        password_data = {
            "id": create_test_admin.id,
            "oldpassword": "anypassword",
            "password": "newpassword123"
        }
        response = client.post("/api/users/password/", json=password_data, headers=auth_headers)
        assert response.status_code == 403

    def test_update_password_admin_cannot_change_other_user_password(self, client: TestClient, admin_auth_headers: dict, create_test_user):
        password_data = {
            "id": create_test_user.id,
            "oldpassword": "anypassword",
            "password": "newpassword123"
        }
        response = client.post("/api/users/password/", json=password_data, headers=admin_auth_headers)
        assert response.status_code == 403

    def test_update_password_unauthorized(self, client: TestClient, create_test_user):
        password_data = {
            "id": create_test_user.id,
            "oldpassword": "oldpassword",
            "password": "newpassword123"
        }
        response = client.post("/api/users/password/", json=password_data)
        assert response.status_code == 401

    def test_update_password_missing_fields(self, client: TestClient, auth_headers: dict, create_test_user):
        password_data = {
            "id": create_test_user.id,
            "oldpassword": "oldpassword"
        }
        response = client.post("/api/users/password/", json=password_data, headers=auth_headers)
        assert response.status_code == 422


class TestAuthenticationScenarios:
    def test_expired_token(self, client: TestClient, expired_token_headers: dict):
        response = client.get("/api/users/me", headers=expired_token_headers)
        assert response.status_code == 401

    def test_invalid_token(self, client: TestClient, invalid_token_headers: dict):
        response = client.get("/api/users/me", headers=invalid_token_headers)
        assert response.status_code == 401

    def test_no_token(self, client: TestClient):
        response = client.get("/api/users/me")
        assert response.status_code == 401

    def test_malformed_authorization_header(self, client: TestClient):
        headers = {"Authorization": "InvalidFormat token"}
        response = client.get("/api/users/me", headers=headers)
        assert response.status_code == 401

    def test_empty_authorization_header(self, client: TestClient):
        headers = {"Authorization": ""}
        response = client.get("/api/users/me", headers=headers)
        assert response.status_code == 401
