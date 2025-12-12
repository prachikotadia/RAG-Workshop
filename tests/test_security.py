"""
Security and compliance tests.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.db.base import Base, get_db
from app.db import models
from app.utils.security import get_password_hash
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def test_db():
    """Create test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = TestingSessionLocal()
    
    # Create test user
    user = models.User(
        email="test@example.com",
        hashed_password=get_password_hash("test_password_123")
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    
    def override_get_db():
        try:
            yield session
        finally:
            pass
    
    return session, override_get_db


@pytest.fixture
def client(test_db):
    """Create test client."""
    _, override_get_db = test_db
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_rate_limiting(client, test_db):
    """Test that rate limiting works."""
    # Login first
    login_response = client.post(
        "/auth/login",
        data={"username": "test@example.com", "password": "test_password_123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Make many requests quickly
    headers = {"Authorization": f"Bearer {token}"}
    responses = []
    for i in range(70):  # More than the 60/minute limit
        response = client.get("/documents", headers=headers)
        responses.append(response.status_code)
    
    # Should eventually get 429 (Too Many Requests)
    assert 429 in responses


def test_gdpr_data_export(client, test_db):
    """Test GDPR data export endpoint."""
    # Login
    login_response = client.post(
        "/auth/login",
        data={"username": "test@example.com", "password": "test_password_123"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Export data
    export_response = client.get("/admin/gdpr/export", headers=headers)
    assert export_response.status_code == 200
    assert export_response.headers["content-type"] == "application/json"
    
    # Verify content
    import json
    data = json.loads(export_response.content)
    assert "user" in data
    assert "documents" in data
    assert "chat_sessions" in data
    assert "audit_logs" in data


def test_gdpr_account_deletion(client, test_db):
    """Test GDPR account deletion."""
    # Login
    login_response = client.post(
        "/auth/login",
        data={"username": "test@example.com", "password": "test_password_123"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Delete account
    delete_response = client.delete("/admin/gdpr/delete-account", headers=headers)
    assert delete_response.status_code == 200
    
    # Verify user is deleted
    # Try to login again - should fail
    login_again = client.post(
        "/auth/login",
        data={"username": "test@example.com", "password": "test_password_123"}
    )
    assert login_again.status_code == 401


def test_audit_logging(client, test_db):
    """Test that audit logs are created."""
    session, _ = test_db
    
    # Login
    login_response = client.post(
        "/auth/login",
        data={"username": "test@example.com", "password": "test_password_123"}
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Perform an action
    client.get("/documents", headers=headers)
    
    # Check audit logs
    from app.utils.audit_log import AuditLog
    logs = session.query(AuditLog).all()
    assert len(logs) > 0
    
    # Verify log structure
    log = logs[0]
    assert log.user_id is not None
    assert log.action is not None
    assert log.endpoint is not None

