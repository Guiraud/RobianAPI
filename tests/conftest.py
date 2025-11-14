"""
Configuration pytest pour les tests RobianAPI
"""
import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport

from api.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for testing
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_debate_data():
    """Sample debate data for testing"""
    return {
        "title": "Test Debate on Climate Change",
        "description": "A test debate about environmental policies",
        "type": "commission",
        "date": "2024-01-15",
        "source_url": "https://videos.assemblee-nationale.fr/test/12345",
        "commission": "Développement durable",
        "speakers": ["Marie Dupont", "Jean Martin"],
        "tags": ["environnement", "climat"],
    }
