"""
Python SDK for RAG Workspace API.
"""
import httpx
from typing import Optional, List, Dict, Any
from pathlib import Path


class RAGWorkspaceClient:
    """Client for interacting with RAG Workspace API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_token: Optional[str] = None):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of the API
            api_token: API access token (from /auth/login)
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_token}"} if api_token else {},
            timeout=30.0
        )
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login and get access token."""
        response = await self._client.post(
            "/auth/login",
            data={"username": email, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.api_token = data["access_token"]
        self._client.headers["Authorization"] = f"Bearer {self.api_token}"
        return data
    
    async def upload_document(self, file_path: Path) -> List[Dict[str, Any]]:
        """Upload a document."""
        with open(file_path, "rb") as f:
            files = {"files": (file_path.name, f, "application/octet-stream")}
            response = await self._client.post("/documents/upload", files=files)
            response.raise_for_status()
            return response.json()
    
    async def list_documents(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all documents."""
        params = {"search": search} if search else {}
        response = await self._client.get("/documents", params=params)
        response.raise_for_status()
        return response.json()
    
    async def send_message(self, session_id: int, content: str) -> Dict[str, Any]:
        """Send a message to a chat session."""
        response = await self._client.post(
            f"/chat/sessions/{session_id}/message",
            json={"content": content}
        )
        response.raise_for_status()
        return response.json()
    
    async def create_session(self, title: Optional[str] = None) -> Dict[str, Any]:
        """Create a new chat session."""
        response = await self._client.post(
            "/chat/sessions",
            json={"title": title}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get usage analytics."""
        response = await self._client.get(f"/admin/analytics/usage?days={days}")
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


# Example usage:
"""
from sdk.rag_workspace_sdk import RAGWorkspaceClient

async def main():
    client = RAGWorkspaceClient()
    
    # Login
    await client.login("user@example.com", "password")
    
    # Upload document
    await client.upload_document(Path("document.pdf"))
    
    # Create chat session
    session = await client.create_session("My Session")
    
    # Send message
    response = await client.send_message(session["id"], "What is in my documents?")
    print(response)
    
    await client.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
"""

