"""
Tests for health check endpoints
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test the root endpoint returns API info"""
    response = await client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert "message" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "operational"
    assert "features" in data
    assert "endpoints" in data


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    """Test the health check endpoint"""
    response = await client.get("/health/")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] in ["healthy", "degraded"]


@pytest.mark.asyncio
async def test_api_docs_available(client: AsyncClient):
    """Test that API documentation is available"""
    response = await client.get("/docs")

    # Docs should be available in development
    assert response.status_code in [200, 307]  # 307 if redirected
