"""
API Client — HTTP client for communicating with the mock environment.

Provides a clean interface for agents to call mock APIs
(catalog, CRM, ads, messaging, payments) through the mock server.
"""

import httpx
from typing import Any, Dict, Optional


class MockAPIClient:
    """
    HTTP client for the Mizan mock environment.

    Usage:
        client = MockAPIClient("http://localhost:8100")
        products = await client.get("/api/catalog/products")
    """

    def __init__(self, base_url: str = "http://localhost:8100"):
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def get(self, path: str, **kwargs) -> Dict[str, Any]:
        """GET request to mock server."""
        client = self._ensure_client()
        response = await client.get(path, **kwargs)
        response.raise_for_status()
        return response.json()

    async def post(self, path: str, json: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """POST request to mock server."""
        client = self._ensure_client()
        response = await client.post(path, json=json, **kwargs)
        response.raise_for_status()
        return response.json()

    async def reset_state(self) -> None:
        """Reset mock server state between benchmark runs."""
        await self.post("/api/state/reset")

    async def create_snapshot(self) -> str:
        """Create a state snapshot and return its ID."""
        result = await self.post("/api/state/snapshot")
        return result.get("snapshot_id", "")

    async def restore_snapshot(self, snapshot_id: str) -> None:
        """Restore mock server state from a snapshot."""
        await self.post(f"/api/state/restore/{snapshot_id}")

    def _ensure_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
            )
        return self._client
