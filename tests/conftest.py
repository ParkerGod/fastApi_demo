import os
import sys
from datetime import datetime, timedelta
from typing import Generator

import jwt
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from sql_app.database import Base, get_db
from sql_app import models
from sql_app.schemas import schemas_user
from sql_app.cruds import users as crud_users
from routers.auth import ALGORITHM, create_access_token
from sql_app.cruds.users import SECRET_KEY

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> TestClient:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    return {
        "email": "test@example.com",
        "password": "testpassword123",
    }


@pytest.fixture
def test_admin_data():
    return {
        "email": "admin@example.com",
        "password": "adminpassword123",
    }


@pytest.fixture
def test_inactive_user_data():
    return {
        "email": "inactive@example.com",
        "password": "inactivepassword123",
    }


@pytest.fixture
def create_test_user(db_session: Session, test_user_data: dict):
    user_create = schemas_user.UserCreate(**test_user_data)
    user = crud_users.create_user(db_session, user_create)
    return user


@pytest.fixture
def create_test_admin(db_session: Session, test_admin_data: dict):
    user_create = schemas_user.UserCreate(**test_admin_data)
    user = crud_users.create_user(db_session, user_create)
    user.role = "admin"
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def create_inactive_user(db_session: Session, test_inactive_user_data: dict):
    user_create = schemas_user.UserCreate(**test_inactive_user_data)
    user = crud_users.create_user(db_session, user_create)
    user.is_active = False
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(create_test_user):
    access_token = create_access_token(data={"sub": create_test_user.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_auth_headers(create_test_admin):
    access_token = create_access_token(data={"sub": create_test_admin.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def inactive_auth_headers(create_inactive_user):
    access_token = create_access_token(data={"sub": create_inactive_user.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def expired_token_headers(create_test_user):
    expired_delta = timedelta(minutes=-10)
    access_token = create_access_token(
        data={"sub": create_test_user.email},
        expires_delta=expired_delta
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def invalid_token_headers():
    return {"Authorization": "Bearer invalid_token_here"}


def generate_test_token(email: str, expires_delta: timedelta = None):
    return create_access_token(data={"sub": email}, expires_delta=expires_delta)


def override_dependency(user: models.User):
    def _override():
        return user
    return _override
