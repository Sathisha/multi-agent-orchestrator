import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from shared.services.auth import AuthService
from shared.models.user import User
from shared.schemas.auth import UserRegister

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, async_db_session: AsyncSession):
    """Test successful user registration."""
    register_data = {
        "email": "newuser@example.com",
        "password": "SecurePassword123",
        "full_name": "New User"
    }
    response = await client.post("/api/v1/auth/register", json=register_data)
    
    assert response.status_code == 201
    response_json = response.json()
    assert response_json["email"] == register_data["email"]
    assert response_json["full_name"] == register_data["full_name"]
    assert response_json["is_active"] is True

    # Verify user in DB
    auth_service = AuthService(async_db_session)
    user = await auth_service.get_user_by_email(register_data["email"])
    assert user is not None
    assert user.email == register_data["email"]
    assert user.is_active is True
    # In a real test, also check default role assignment.
    # This might require mocking RBAC service or checking roles table.


@pytest.mark.asyncio
async def test_register_existing_email(client: AsyncClient, async_db_session: AsyncSession):
    """Test registration with an email that already exists."""
    # First, register a user
    auth_service = AuthService(async_db_session)
    await auth_service.register_user(
        email="existing@example.com",
        password="Password123",
        full_name="Existing User"
    )
    
    register_data = {
        "email": "existing@example.com",
        "password": "AnotherPassword123",
        "full_name": "Another User"
    }
    response = await client.post("/api/v1/auth/register", json=register_data)
    
    assert response.status_code == 400
    assert "User with email existing@example.com already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_invalid_password_too_short(client: AsyncClient):
    """Test registration with a password that is too short."""
    register_data = {
        "email": "shortpass@example.com",
        "password": "short", # Less than 8 characters
        "full_name": "Short Pass User"
    }
    response = await client.post("/api/v1/auth/register", json=register_data)
    
    assert response.status_code == 422 # Unprocessable Entity
    assert "Password must be at least 8 characters long" in response.json()["detail"][0]["msg"]


@pytest.mark.asyncio
async def test_register_invalid_password_missing_chars(client: AsyncClient):
    """Test registration with a password missing required character types."""
    register_data = {
        "email": "weakpass@example.com",
        "password": "password", # Missing uppercase and digit
        "full_name": "Weak Pass User"
    }
    response = await client.post("/api/v1/auth/register", json=register_data)
    
    assert response.status_code == 422
    assert "Password must contain at least one uppercase letter, one lowercase letter, and one digit" in response.json()["detail"][0]["msg"]


@pytest.mark.asyncio
async def test_register_invalid_email_format(client: AsyncClient):
    """Test registration with an invalid email format."""
    register_data = {
        "email": "invalid-email",
        "password": "SecurePassword123",
        "full_name": "Invalid Email User"
    }
    response = await client.post("/api/v1/auth/register", json=register_data)
    
    assert response.status_code == 422
    assert "value is not a valid email address" in response.json()["detail"][0]["msg"]
