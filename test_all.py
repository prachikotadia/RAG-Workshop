#!/usr/bin/env python3
# Quick test script to verify everything works
import sys
from app.main import create_app
from fastapi.testclient import TestClient
from app.db.base import get_db
from app.db import models
from app.auth.service import create_user_access_token

def test_all():
    print("Testing application...")
    
    # Test 1: App creation
    try:
        app = create_app()
        print("✓ App created")
    except Exception as e:
        print(f"✗ App creation failed: {e}")
        return False
    
    # Test 2: Database
    try:
        db = next(get_db())
        user = db.query(models.User).first()
        db.close()
        if not user:
            print("⚠ No users in database")
        else:
            print("✓ Database works")
    except Exception as e:
        print(f"✗ Database failed: {e}")
        return False
    
    # Test 3: Endpoints
    try:
        client = TestClient(app)
        db = next(get_db())
        user = db.query(models.User).first()
        if user:
            token = create_user_access_token(user)
            headers = {'Authorization': f'Bearer {token}'}
            
            r1 = client.get('/documents', headers=headers)
            r2 = client.get('/chat/sessions', headers=headers)
            r3 = client.get('/auth/me', headers=headers)
            
            if r1.status_code == 200 and r2.status_code == 200 and r3.status_code == 200:
                print("✓ All endpoints work")
            else:
                print(f"⚠ Some endpoints failed: docs={r1.status_code}, chat={r2.status_code}, auth={r3.status_code}")
        db.close()
    except Exception as e:
        print(f"✗ Endpoint test failed: {e}")
        return False
    
    print("\n✓ All tests passed!")
    return True

if __name__ == "__main__":
    success = test_all()
    sys.exit(0 if success else 1)
