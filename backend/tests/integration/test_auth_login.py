import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Import necessary models and services for test user creation
from shared.services.auth import AuthService
from shared.models.user import User, UserStatus
from shared.schemas.auth import UserRegister
from main import app


# Fixture for creating a test admin user and providing credentials
@pytest.fixture
async def create_admin_user_in_db(async_db_session: AsyncSession):
    auth_service = AuthService(async_db_session)
    # Check if admin user already exists to prevent re-creation if fixture is somehow called multiple times
    existing_admin = await auth_service.get_user_by_email("admin@example.com")
    if not existing_admin:
        admin_user_data = UserRegister(
            email="admin@example.com",
            password="admin",
            full_name="Admin User"
        )
        admin_user = await auth_service.register_user(
            email=admin_user_data.email,
            password=admin_user_data.password,
            full_name=admin_user_data.full_name
        )
        admin_user.is_system_admin = True
        await async_db_session.commit()
    
    return {"email": "admin@example.com", "password": "admin"}


# Fixture for creating an inactive test user
@pytest.fixture
async def create_inactive_user_in_db(async_db_session: AsyncSession):
    auth_service = AuthService(async_db_session)
    inactive_user_data = UserRegister(
        email="inactive@example.com",
        password="testpassword",
        full_name="Inactive User"
    )
    inactive_user = await auth_service.register_user(
        email=inactive_user_data.email,
        password=inactive_user_data.password,
        full_name=inactive_user_data.full_name
    )
    inactive_user.is_active = False
    await async_db_session.commit()
    return {"email": "inactive@example.com", "password": "testpassword"}


# --- Test Cases for Login Endpoint ---

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, create_admin_user_in_db: dict):
    """Test successful login with valid credentials."""
    admin_credentials = create_admin_user_in_db
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_credentials["email"], "password": admin_credentials["password"]}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    assert response.json()["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_incorrect_password(client: AsyncClient, create_admin_user_in_db: dict):
    """Test login with an incorrect password."""
    admin_credentials = create_admin_user_in_db
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_credentials["email"], "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

@pytest.mark.asyncio
async def test_login_non_existent_email(client: AsyncClient):
    """Test login with a non-existent email."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "anypassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, create_inactive_user_in_db: dict):
    """Test login with an inactive user."""
    inactive_user_credentials = create_inactive_user_in_db
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": inactive_user_credentials["email"], "password": inactive_user_credentials["password"]}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

@pytest.mark.asyncio
async def test_login_invalid_email_format(client: AsyncClient):
    """Test login with an invalid email format."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "invalid-email", "password": "testpassword"}
    )
    assert response.status_code == 422 # Unprocessable Entity due to Pydantic validation
    assert "value is not a valid email address" in response.json()["detail"][0]["msg"]

