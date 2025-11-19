"""Tests for authentication flow with real behavior validation."""
import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.auth.service import (
    create_user,
    authenticate_user,
    get_user_by_email,
    create_user_access_token
)
from app.auth.jwt import create_access_token, decode_access_token
from app.db.schemas import UserCreate
from app.utils.security import verify_password, get_password_hash
from app.db.base import SessionLocal, Base, engine
from app.db import models


@pytest.fixture(scope="function")
def db():
    """Create a fresh database session for each test."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up tables
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user_data():
    """Fixture for test user data."""
    return {
        "email": "test@example.com",
        "password": "test_password_123"
    }


def test_password_hashing_security():
    """Test password hashing with real security behavior."""
    password = "test_password_123"
    hashed = get_password_hash(password)
    
    # Real behavior: Hash should be different from password
    assert hashed != password, "Hash should not equal plain password"
    assert len(hashed) > 50, "Hash should be substantial length"
    
    # Real behavior: Should verify correctly
    assert verify_password(password, hashed), "Correct password should verify"
    assert not verify_password("wrong_password", hashed), "Wrong password should not verify"
    assert not verify_password("", hashed), "Empty password should not verify"
    assert not verify_password(password.upper(), hashed), "Case-sensitive passwords should not verify"


def test_password_hashing_salt_uniqueness():
    """Test that password hashing uses unique salts (real behavior)."""
    password = "test_password_123"
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)
    
    # Real behavior: Hashes should be different due to salt
    assert hash1 != hash2, "Same password should produce different hashes (salt)"
    
    # Real behavior: Both should verify correctly
    assert verify_password(password, hash1), "First hash should verify"
    assert verify_password(password, hash2), "Second hash should verify"


def test_password_hashing_long_passwords():
    """Test password hashing with long passwords (72-byte limit)."""
    # Real behavior: Bcrypt has 72-byte limit
    short_password = "short"
    long_password = "a" * 100  # 100 bytes
    
    short_hash = get_password_hash(short_password)
    long_hash = get_password_hash(long_password)
    
    # Both should hash successfully (long one truncated)
    assert verify_password(short_password, short_hash), "Short password should verify"
    assert verify_password(long_password, long_hash), "Long password should verify (truncated)" 


def test_create_user_success(db, test_user_data):
    """Test user creation with real database behavior."""
    # Real behavior: Should create user in database
    user_create = UserCreate(**test_user_data)
    user = create_user(db, user_create)
    
    assert user.id is not None, "User should have ID"
    assert user.email == test_user_data["email"], "User email should match"
    assert user.hashed_password != test_user_data["password"], "Password should be hashed"
    assert len(user.hashed_password) > 0, "Hashed password should not be empty"
    
    # Real behavior: Password should verify
    assert verify_password(test_user_data["password"], user.hashed_password), \
        "Stored password hash should verify"


def test_create_user_duplicate_email(db, test_user_data):
    """Test user creation fails with duplicate email (real behavior)."""
    # Create first user
    user_create = UserCreate(**test_user_data)
    create_user(db, user_create)
    
    # Real behavior: Duplicate email should raise HTTPException
    with pytest.raises(HTTPException) as exc_info:
        create_user(db, user_create)
    
    assert exc_info.value.status_code == 400, "Should return 400 for duplicate email"
    assert "already registered" in str(exc_info.value.detail).lower(), \
        "Error message should mention email already registered"


def test_authenticate_user_success(db, test_user_data):
    """Test user authentication with real database behavior."""
    # Create user first
    user_create = UserCreate(**test_user_data)
    created_user = create_user(db, user_create)
    
    # Real behavior: Should authenticate with correct credentials
    authenticated_user = authenticate_user(
        db,
        test_user_data["email"],
        test_user_data["password"]
    )
    
    assert authenticated_user is not None, "Should return user for correct credentials"
    assert authenticated_user.id == created_user.id, "Should return same user"
    assert authenticated_user.email == test_user_data["email"], "Email should match"


def test_authenticate_user_wrong_password(db, test_user_data):
    """Test authentication fails with wrong password (real behavior)."""
    # Create user first
    user_create = UserCreate(**test_user_data)
    create_user(db, user_create)
    
    # Real behavior: Should return None for wrong password
    authenticated_user = authenticate_user(
        db,
        test_user_data["email"],
        "wrong_password"
    )
    
    assert authenticated_user is None, "Should return None for wrong password"


def test_authenticate_user_nonexistent_email(db):
    """Test authentication fails for nonexistent email (real behavior)."""
    # Real behavior: Should return None for nonexistent email
    authenticated_user = authenticate_user(
        db,
        "nonexistent@example.com",
        "any_password"
    )
    
    assert authenticated_user is None, "Should return None for nonexistent email"


def test_get_user_by_email(db, test_user_data):
    """Test getting user by email with real database behavior."""
    # Create user first
    user_create = UserCreate(**test_user_data)
    created_user = create_user(db, user_create)
    
    # Real behavior: Should find user by email
    found_user = get_user_by_email(db, test_user_data["email"])
    
    assert found_user is not None, "Should find user"
    assert found_user.id == created_user.id, "Should return same user"
    assert found_user.email == test_user_data["email"], "Email should match"
    
    # Real behavior: Should return None for nonexistent email
    not_found = get_user_by_email(db, "nonexistent@example.com")
    assert not_found is None, "Should return None for nonexistent email"


def test_create_user_access_token(db, test_user_data):
    """Test JWT token creation with real behavior."""
    # Create user first
    user_create = UserCreate(**test_user_data)
    user = create_user(db, user_create)
    
    # Real behavior: Should create valid JWT token
    token = create_user_access_token(user)
    
    assert isinstance(token, str), "Token should be string"
    assert len(token) > 0, "Token should not be empty"
    
    # Real behavior: Should decode to correct payload
    payload = decode_access_token(token)
    assert payload["sub"] == user.email, "Token should contain user email"
    assert payload["user_id"] == user.id, "Token should contain user ID"
    assert "exp" in payload, "Token should have expiration"
    assert "iat" in payload, "Token should have issued-at time"


def test_signup_login_flow(db, test_user_data):
    """Test complete signup and login flow (real behavior)."""
    # Step 1: Signup
    user_create = UserCreate(**test_user_data)
    user = create_user(db, user_create)
    
    assert user.id is not None, "User should be created"
    assert user.email == test_user_data["email"], "Email should match"
    
    # Step 2: Login
    authenticated_user = authenticate_user(
        db,
        test_user_data["email"],
        test_user_data["password"]
    )
    
    assert authenticated_user is not None, "Should authenticate successfully"
    assert authenticated_user.id == user.id, "Should be same user"
    
    # Step 3: Generate access token
    token = create_user_access_token(authenticated_user)
    assert len(token) > 0, "Should generate token"
    
    # Step 4: Verify token
    payload = decode_access_token(token)
    assert payload["sub"] == test_user_data["email"], "Token should contain email"
    assert payload["user_id"] == user.id, "Token should contain user ID"

