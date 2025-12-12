"""
Load testing with Locust.

Run with: locust -f tests/load/locustfile.py --host=http://localhost:8000
"""
from locust import HttpUser, task, between
import random
import string


def generate_random_string(length=10):
    """Generate random string for test data."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


class RAGWorkspaceUser(HttpUser):
    """Simulated user for load testing."""
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Login and get auth token."""
        # Signup or login
        email = f"test_{generate_random_string()}@example.com"
        password = "test_password_123"
        
        # Try signup
        signup_response = self.client.post(
            "/auth/signup",
            json={"email": email, "password": password}
        )
        
        if signup_response.status_code == 201:
            # New user created
            login_response = self.client.post(
                "/auth/login",
                data={"username": email, "password": password}
            )
        else:
            # User exists, try login
            login_response = self.client.post(
                "/auth/login",
                data={"username": email, "password": password}
            )
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            self.client.headers = {"Authorization": f"Bearer {token}"}
    
    @task(3)
    def list_documents(self):
        """List documents."""
        self.client.get("/documents")
    
    @task(2)
    def list_chat_sessions(self):
        """List chat sessions."""
        self.client.get("/chat/sessions")
    
    @task(1)
    def get_analytics(self):
        """Get analytics."""
        self.client.get("/admin/analytics/usage?days=30")
    
    @task(1)
    def create_chat_session(self):
        """Create a new chat session."""
        self.client.post("/chat/sessions", json={"title": "Test Session"})
    
    @task(1)
    def send_chat_message(self):
        """Send a chat message."""
        # First create a session
        session_response = self.client.post("/chat/sessions", json={"title": "Load Test"})
        if session_response.status_code == 201:
            session_id = session_response.json()["id"]
            self.client.post(
                f"/chat/sessions/{session_id}/message",
                json={"content": "What is machine learning?"}
            )


class DocumentUploadUser(HttpUser):
    """User focused on document operations."""
    wait_time = between(2, 5)
    
    def on_start(self):
        """Login."""
        email = f"upload_{generate_random_string()}@example.com"
        password = "test_password_123"
        
        self.client.post("/auth/signup", json={"email": email, "password": password})
        login_response = self.client.post(
            "/auth/login",
            data={"username": email, "password": password}
        )
        
        if login_response.status_code == 200:
            token = login_response.json()["access_token"]
            self.client.headers = {"Authorization": f"Bearer {token}"}
    
    @task(5)
    def list_documents(self):
        """List documents."""
        self.client.get("/documents")
    
    @task(1)
    def upload_document(self):
        """Upload a test document."""
        # Create a simple text file
        files = {
            "files": ("test.txt", "This is a test document for load testing.", "text/plain")
        }
        self.client.post("/documents/upload", files=files)

