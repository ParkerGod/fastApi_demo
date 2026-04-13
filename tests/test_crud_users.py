import pytest
from sqlalchemy.orm import Session

from sql_app.cruds import users as crud_users
from sql_app.schemas import schemas_user
from sql_app.cruds.users import SECRET_KEY, get_password_hash, verify_password


class TestGetUser:
    def test_get_user_by_id_success(self, db_session: Session, create_test_user):
        user = crud_users.get_user(db_session, create_test_user.id)
        assert user is not None
        assert user.id == create_test_user.id
        assert user.email == create_test_user.email

    def test_get_user_by_id_not_found(self, db_session: Session):
        user = crud_users.get_user(db_session, 99999)
        assert user is None

    def test_get_user_by_id_negative_id(self, db_session: Session):
        user = crud_users.get_user(db_session, -1)
        assert user is None

    def test_get_user_by_id_zero(self, db_session: Session):
        user = crud_users.get_user(db_session, 0)
        assert user is None


class TestGetUserByEmail:
    def test_get_user_by_email_success(self, db_session: Session, create_test_user):
        user = crud_users.get_user_by_email(db_session, create_test_user.email)
        assert user is not None
        assert user.email == create_test_user.email

    def test_get_user_by_email_not_found(self, db_session: Session):
        user = crud_users.get_user_by_email(db_session, "nonexistent@example.com")
        assert user is None

    def test_get_user_by_email_empty_string(self, db_session: Session):
        user = crud_users.get_user_by_email(db_session, "")
        assert user is None

    def test_get_user_by_email_invalid_format(self, db_session: Session):
        user = crud_users.get_user_by_email(db_session, "invalid-email-format")
        assert user is None


class TestGetUsers:
    def test_get_users_success(self, db_session: Session, create_test_user, create_test_admin):
        users = crud_users.get_users(db_session)
        assert len(users) == 2

    def test_get_users_empty_database(self, db_session: Session):
        users = crud_users.get_users(db_session)
        assert users == []

    def test_get_users_pagination_skip(self, db_session: Session):
        for i in range(5):
            user_create = schemas_user.UserCreate(
                email=f"user{i}@example.com",
                password="password123"
            )
            crud_users.create_user(db_session, user_create)

        users = crud_users.get_users(db_session, skip=2, limit=2)
        assert len(users) == 2

    def test_get_users_pagination_limit(self, db_session: Session):
        for i in range(10):
            user_create = schemas_user.UserCreate(
                email=f"user{i}@example.com",
                password="password123"
            )
            crud_users.create_user(db_session, user_create)

        users = crud_users.get_users(db_session, skip=0, limit=5)
        assert len(users) == 5

    def test_get_users_skip_exceeds_count(self, db_session: Session, create_test_user):
        users = crud_users.get_users(db_session, skip=100, limit=10)
        assert users == []


class TestGetUserByLogin:
    def test_get_user_by_login_success(self, db_session: Session, test_user_data: dict):
        user_create = schemas_user.UserCreate(**test_user_data)
        crud_users.create_user(db_session, user_create)

        user = crud_users.get_user_by_login(
            db_session,
            test_user_data["email"],
            test_user_data["password"]
        )
        assert user is not False
        assert user.email == test_user_data["email"]

    def test_get_user_by_login_wrong_email(self, db_session: Session, create_test_user):
        user = crud_users.get_user_by_login(
            db_session,
            "wrong@example.com",
            "testpassword123"
        )
        assert user is False

    def test_get_user_by_login_wrong_password(self, db_session: Session, create_test_user, test_user_data: dict):
        user = crud_users.get_user_by_login(
            db_session,
            test_user_data["email"],
            "wrongpassword"
        )
        assert user is False

    def test_get_user_by_login_empty_credentials(self, db_session: Session):
        user = crud_users.get_user_by_login(db_session, "", "")
        assert user is False


class TestCreateUser:
    def test_create_user_success(self, db_session: Session, test_user_data: dict):
        user_create = schemas_user.UserCreate(**test_user_data)
        user = crud_users.create_user(db_session, user_create)

        assert user.id is not None
        assert user.email == test_user_data["email"]
        assert user.username == test_user_data["email"].split("@")[0]
        assert user.role == "general"
        assert user.is_active is True

    def test_create_user_password_hashed(self, db_session: Session, test_user_data: dict):
        user_create = schemas_user.UserCreate(**test_user_data)
        user = crud_users.create_user(db_session, user_create)

        assert user.hashed_password != test_user_data["password"]
        expected_hash_input = test_user_data["password"] + SECRET_KEY
        assert verify_password(expected_hash_input, user.hashed_password)

    def test_create_user_email_without_at_symbol(self, db_session: Session):
        user_create = schemas_user.UserCreate(
            email="noemailformat",
            password="password123"
        )
        user = crud_users.create_user(db_session, user_create)
        assert user.username == "noemailformat"

    def test_create_user_default_values(self, db_session: Session, test_user_data: dict):
        user_create = schemas_user.UserCreate(**test_user_data)
        user = crud_users.create_user(db_session, user_create)

        assert user.role == "general"
        assert user.is_active is True
        assert user.avatar is None
        assert user.frequency_max == 600


class TestDeleteUser:
    def test_delete_user_success(self, db_session: Session, create_test_user):
        res = crud_users.delete_user(db_session, create_test_user.id)
        assert res == 1

        user = crud_users.get_user(db_session, create_test_user.id)
        assert user is None

    def test_delete_user_not_found(self, db_session: Session):
        res = crud_users.delete_user(db_session, 99999)
        assert res == 0

    def test_delete_user_twice(self, db_session: Session, create_test_user):
        res1 = crud_users.delete_user(db_session, create_test_user.id)
        assert res1 == 1

        res2 = crud_users.delete_user(db_session, create_test_user.id)
        assert res2 == 0

    def test_delete_user_negative_id(self, db_session: Session):
        res = crud_users.delete_user(db_session, -1)
        assert res == 0


class TestUpdateUser:
    def test_update_user_success(self, db_session: Session, create_test_user):
        update_data = schemas_user.User(
            id=create_test_user.id,
            email="updated@example.com",
            username="updateduser",
            avatar="https://example.com/avatar.png",
            role="admin",
            is_active=True,
            frequency_max=1000
        )
        res = crud_users.update_user(db_session, update_data)
        assert res == 1

        updated_user = crud_users.get_user(db_session, create_test_user.id)
        assert updated_user.email == "updated@example.com"
        assert updated_user.username == "updateduser"
        assert updated_user.avatar == "https://example.com/avatar.png"
        assert updated_user.role == "admin"

    def test_update_user_not_found(self, db_session: Session):
        update_data = schemas_user.User(
            id=99999,
            email="notfound@example.com",
            username="notfound",
            avatar=None,
            role="general",
            is_active=True,
            frequency_max=600
        )
        res = crud_users.update_user(db_session, update_data)
        assert res == 0

    def test_update_user_partial(self, db_session: Session, create_test_user):
        original_email = create_test_user.email
        update_data = schemas_user.User(
            id=create_test_user.id,
            email=original_email,
            username="newusername",
            avatar=create_test_user.avatar,
            role=create_test_user.role,
            is_active=create_test_user.is_active,
            frequency_max=create_test_user.frequency_max
        )
        res = crud_users.update_user(db_session, update_data)
        assert res == 1

        updated_user = crud_users.get_user(db_session, create_test_user.id)
        assert updated_user.username == "newusername"
        assert updated_user.email == original_email


class TestUpdateUserPassword:
    def test_update_password_success(self, db_session: Session, test_user_data: dict):
        user_create = schemas_user.UserCreate(**test_user_data)
        user = crud_users.create_user(db_session, user_create)

        password_update = schemas_user.UserPassWord(
            id=user.id,
            oldpassword=test_user_data["password"],
            password="newpassword123"
        )
        res = crud_users.update_user_password(db_session, password_update)
        assert res == 1

        login_user = crud_users.get_user_by_login(
            db_session,
            test_user_data["email"],
            "newpassword123"
        )
        assert login_user is not False

    def test_update_password_wrong_old_password(self, db_session: Session, create_test_user):
        password_update = schemas_user.UserPassWord(
            id=create_test_user.id,
            oldpassword="wrongoldpassword",
            password="newpassword123"
        )
        res = crud_users.update_user_password(db_session, password_update)
        assert res is False

    def test_update_password_user_not_found(self, db_session: Session):
        password_update = schemas_user.UserPassWord(
            id=99999,
            oldpassword="oldpassword",
            password="newpassword123"
        )
        res = crud_users.update_user_password(db_session, password_update)
        assert res is False

    def test_update_password_verify_old_still_works(self, db_session: Session, test_user_data: dict):
        user_create = schemas_user.UserCreate(**test_user_data)
        user = crud_users.create_user(db_session, user_create)

        password_update = schemas_user.UserPassWord(
            id=user.id,
            oldpassword=test_user_data["password"],
            password="newpassword123"
        )
        crud_users.update_user_password(db_session, password_update)

        old_login = crud_users.get_user_by_login(
            db_session,
            test_user_data["email"],
            test_user_data["password"]
        )
        assert old_login is False


class TestPasswordHash:
    def test_get_password_hash(self):
        password = "testpassword123"
        hashed = get_password_hash(password + SECRET_KEY)
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        password = "testpassword123"
        hashed = get_password_hash(password + SECRET_KEY)
        assert verify_password(password + SECRET_KEY, hashed) is True

    def test_verify_password_incorrect(self):
        password = "testpassword123"
        hashed = get_password_hash(password + SECRET_KEY)
        assert verify_password("wrongpassword" + SECRET_KEY, hashed) is False

    def test_password_hash_unique(self):
        password = "testpassword123"
        hash1 = get_password_hash(password + SECRET_KEY)
        hash2 = get_password_hash(password + SECRET_KEY)
        assert hash1 != hash2

    def test_verify_password_empty(self):
        hashed = get_password_hash("" + SECRET_KEY)
        assert verify_password("" + SECRET_KEY, hashed) is True
