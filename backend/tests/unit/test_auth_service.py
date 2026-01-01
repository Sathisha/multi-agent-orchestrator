import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from jose import jwt

from shared.services.auth import AuthService
from shared.models.user import User, UserStatus
from shared.schemas.auth import UserRegister

# Mock settings for JWT
MOCK_SECRET_KEY = "super-secret-test-key"
MOCK_ALGORITHM = "HS256"
MOCK_ACCESS_TOKEN_EXPIRE_MINUTES = 1

# Override settings in AuthService to use mock values
@pytest.fixture(autouse=True)
def mock_auth_service_settings():
    with patch('shared.services.auth.SECRET_KEY', MOCK_SECRET_KEY), \
         patch('shared.services.auth.ALGORITHM', MOCK_ALGORITHM), \
         patch('shared.services.auth.ACCESS_TOKEN_EXPIRE_MINUTES', MOCK_ACCESS_TOKEN_EXPIRE_MINUTES):
        yield

# Fixture for AuthService instance with a mocked session
@pytest.fixture
def auth_service_mocked_session():
    mock_session = AsyncMock(spec=AsyncSession)
    return AuthService(mock_session), mock_session

# --- Test Cases for AuthService methods ---

def test_hash_password():
    """Test that password hashing works."""
    password = "testpassword"
    hashed_password = AuthService.hash_password(password)
    assert isinstance(hashed_password, str)
    assert hashed_password != password # Should not be plain text

def test_verify_password_correct():
    """Test that correct password verifies successfully."""
    password = "testpassword"
    hashed_password = AuthService.hash_password(password)
    assert AuthService.verify_password(password, hashed_password) is True

def test_verify_password_incorrect():
    """Test that incorrect password fails verification."""
    password = "testpassword"
    hashed_password = AuthService.hash_password(password)
    assert AuthService.verify_password("wrongpassword", hashed_password) is False

def test_create_access_token():
    """Test access token creation."""
    user_id = str(uuid4())
    token_data = {"sub": user_id, "email": "test@example.com"}
    token = AuthService.create_access_token(token_data)
    
    assert isinstance(token, str)
    
    decoded_payload = jwt.decode(token, MOCK_SECRET_KEY, algorithms=[MOCK_ALGORITHM])
    assert decoded_payload["sub"] == user_id
    assert decoded_payload["email"] == "test@example.com"
    assert decoded_payload["type"] == "access"
    assert "exp" in decoded_payload

def test_create_refresh_token():
    """Test refresh token creation."""
    user_id = str(uuid4())
    token_data = {"sub": user_id}
    token = AuthService.create_refresh_token(token_data)
    
    assert isinstance(token, str)
    
    decoded_payload = jwt.decode(token, MOCK_SECRET_KEY, algorithms=[MOCK_ALGORITHM])
    assert decoded_payload["sub"] == user_id
    assert decoded_payload["type"] == "refresh"
    assert "exp" in decoded_payload

def test_decode_token_valid(auth_service_mocked_session):
    """Test decoding a valid token."""
    auth_service, _ = auth_service_mocked_session
    user_id = str(uuid4())
    token_data = {"sub": user_id, "type": "access"}
    token = jwt.encode(token_data, MOCK_SECRET_KEY, algorithm=MOCK_ALGORITHM)
    
    decoded_payload = auth_service.decode_token(token)
    assert decoded_payload is not None
    assert decoded_payload["sub"] == user_id
    assert decoded_payload["type"] == "access"

def test_decode_token_invalid_signature(auth_service_mocked_session):
    """Test decoding a token with invalid signature."""
    auth_service, _ = auth_service_mocked_session
    user_id = str(uuid4())
    token_data = {"sub": user_id, "type": "access"}
    # Encode with a different secret key
    token = jwt.encode(token_data, "wrong-secret", algorithm=MOCK_ALGORITHM)
    
    decoded_payload = auth_service.decode_token(token)
    assert decoded_payload is None

def test_decode_token_expired(auth_service_mocked_session):
    """Test decoding an expired token."""
    auth_service, _ = auth_service_mocked_session
    user_id = str(uuid4())
    expired_time = datetime.utcnow() - timedelta(minutes=10)
    token_data = {"sub": user_id, "type": "access", "exp": expired_time.timestamp()}
    token = jwt.encode(token_data, MOCK_SECRET_KEY, algorithm=MOCK_ALGORITHM)
    
    decoded_payload = auth_service.decode_token(token)
    assert decoded_payload is None

@pytest.mark.asyncio
async def test_get_user_by_email_found(auth_service_mocked_session):
    """Test retrieving a user by email when found."""
    auth_service, mock_session = auth_service_mocked_session
    mock_user = User(
        id=uuid4(),
        email="found@example.com",
        username="found@example.com",
        password_hash="hashedpassword",
        is_active=True,
        status=UserStatus.ACTIVE,
        first_name="Found",
        last_name="User"
    )
    
    # Mock the session.execute and result.scalar_one_or_none()
    mock_result = AsyncMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result
    
    user = await auth_service.get_user_by_email("found@example.com")
    assert user is not None
    assert user.email == "found@example.com"
    mock_session.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_user_by_email_not_found(auth_service_mocked_session):
    """Test retrieving a user by email when not found."""
    auth_service, mock_session = auth_service_mocked_session
    
    mock_result = AsyncMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    user = await auth_service.get_user_by_email("notfound@example.com")
    assert user is None
    mock_session.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_user_by_id_found(auth_service_mocked_session):
    """Test retrieving a user by ID when found."""
    auth_service, mock_session = auth_service_mocked_session
    user_id = uuid4()
    mock_user = User(
        id=user_id,
        email="idfound@example.com",
        username="idfound@example.com",
        password_hash="hashedpassword",
        is_active=True,
        status=UserStatus.ACTIVE,
        first_name="ID",
        last_name="User"
    )
    
    mock_result = AsyncMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = mock_user
    mock_session.execute.return_value = mock_result
    
    user = await auth_service.get_user_by_id(user_id)
    assert user is not None
    assert user.id == user_id
    mock_session.execute.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_user_by_id_not_found(auth_service_mocked_session):
    """Test retrieving a user by ID when not found."""
    auth_service, mock_session = auth_service_mocked_session
    
    mock_result = AsyncMock()
    mock_result.unique.return_value.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    user = await auth_service.get_user_by_id(uuid4())
    assert user is None
    mock_session.execute.assert_awaited_once()

@pytest.mark.asyncio
@patch('shared.services.auth.AuthService.get_user_by_email')
@patch('shared.services.auth.AuthService.verify_password')
async def test_authenticate_user_success(
    mock_verify_password: MagicMock,
    mock_get_user_by_email: AsyncMock,
    auth_service_mocked_session
):
    """Test successful user authentication."""
    auth_service, mock_session = auth_service_mocked_session
    
    mock_user = User(
        id=uuid4(),
        email="auth@example.com",
        username="auth@example.com",
        password_hash="hashedpassword",
        is_active=True,
        status=UserStatus.ACTIVE,
        first_name="Auth",
        last_name="User"
    )
    mock_get_user_by_email.return_value = mock_user
    mock_verify_password.return_value = True
    
    user = await auth_service.authenticate_user("auth@example.com", "plainpassword")
    
    assert user is not None
    assert user.email == "auth@example.com"
    mock_get_user_by_email.assert_awaited_once_with("auth@example.com")
    mock_verify_password.assert_called_once_with("plainpassword", "hashedpassword")
    mock_session.commit.assert_awaited_once() # last_login update

@pytest.mark.asyncio
@patch('shared.services.auth.AuthService.get_user_by_email')
async def test_authenticate_user_not_found(
    mock_get_user_by_email: AsyncMock,
    auth_service_mocked_session
):
    """Test authentication for non-existent user."""
    auth_service, _ = auth_service_mocked_session
    mock_get_user_by_email.return_value = None
    
    user = await auth_service.authenticate_user("notfound@example.com", "password")
    
    assert user is None
    mock_get_user_by_email.assert_awaited_once_with("notfound@example.com")

@pytest.mark.asyncio
@patch('shared.services.auth.AuthService.get_user_by_email')
@patch('shared.services.auth.AuthService.verify_password')
async def test_authenticate_user_incorrect_password(
    mock_verify_password: MagicMock,
    mock_get_user_by_email: AsyncMock,
    auth_service_mocked_session
):
    """Test authentication with incorrect password."""
    auth_service, _ = auth_service_mocked_session
    mock_user = User(
        id=uuid4(),
        email="auth@example.com",
        username="auth@example.com",
        password_hash="hashedpassword",
        is_active=True,
        status=UserStatus.ACTIVE,
        first_name="Auth",
        last_name="User"
    )
    mock_get_user_by_email.return_value = mock_user
    mock_verify_password.return_value = False
    
    user = await auth_service.authenticate_user("auth@example.com", "wrongpassword")
    
    assert user is None
    mock_get_user_by_email.assert_awaited_once_with("auth@example.com")
    mock_verify_password.assert_called_once_with("wrongpassword", "hashedpassword")

@pytest.mark.asyncio
@patch('shared.services.auth.AuthService.get_user_by_email')
async def test_authenticate_user_inactive(
    mock_get_user_by_email: AsyncMock,
    auth_service_mocked_session
):
    """Test authentication for an inactive user."""
    auth_service, _ = auth_service_mocked_session
    mock_user = User(
        id=uuid4(),
        email="inactive@example.com",
        username="inactive@example.com",
        password_hash="hashedpassword",
        is_active=False,
        status=UserStatus.INACTIVE,
        first_name="Inactive",
        last_name="User"
    )
    mock_get_user_by_email.return_value = mock_user
    
    user = await auth_service.authenticate_user("inactive@example.com", "password")
    
    assert user is None
    mock_get_user_by_email.assert_awaited_once_with("inactive@example.com")
