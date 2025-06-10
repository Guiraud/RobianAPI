"""
Tests unitaires pour RobianAPI
Tests des modèles, services et API
"""

import pytest
import asyncio
import uuid
from datetime import datetime, date
from unittest.mock import Mock, AsyncMock

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Import de l'application et des modèles
from api.main import app
from api.models import (
    Debate, AudioFile, Collection, Favorite,
    DebateType, DebateStatus,
    get_db_session
)
from api.services import cache_service, websocket_manager


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Fixture pour créer une boucle d'événements pour la session de test"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    """Client HTTP async pour tester l'API"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def mock_db():
    """Mock de la base de données"""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def sample_debate():
    """Débat de test"""
    return Debate(
        id=str(uuid.uuid4()),
        title="Test Debate",
        description="Description de test",
        type=DebateType.SEANCE_PUBLIQUE,
        status=DebateStatus.DISPONIBLE,
        date=date(2025, 6, 9),
        start_time=datetime(2025, 6, 9, 15, 0),
        end_time=datetime(2025, 6, 9, 18, 0),
        duration_minutes=180,
        source_url="https://test.example.com/video123",
        commission=None,
        salle="Test Hall",
        speakers=["Speaker 1", "Speaker 2"],
        ministers=["Test Minister"],
        tags=["test", "debate"],
        view_count=100
    )


@pytest.fixture
def sample_audio_file(sample_debate):
    """Fichier audio de test"""
    return AudioFile(
        id=str(uuid.uuid4()),
        debate_id=sample_debate.id,
        filename="test_audio.mp3",
        file_path="/test/path/test_audio.mp3",
        file_size=1024000,  # 1MB
        format="mp3",
        quality="192k",
        duration_seconds=3600,  # 1 hour
        extraction_status="completed",
        extraction_started_at=datetime.now(),
        extraction_completed_at=datetime.now()
    )


# =============================================================================
# TESTS DES MODÈLES
# =============================================================================

class TestDebateModel:
    """Tests du modèle Debate"""
    
    def test_debate_creation(self, sample_debate):
        """Test de création d'un débat"""
        assert sample_debate.id is not None
        assert sample_debate.title == "Test Debate"
        assert sample_debate.type == DebateType.SEANCE_PUBLIQUE
        assert sample_debate.status == DebateStatus.DISPONIBLE
    
    def test_debate_properties(self, sample_debate):
        """Test des propriétés calculées"""
        assert sample_debate.display_duration == "3h 0min"
        assert not sample_debate.is_live  # Status n'est pas EN_COURS
        assert not sample_debate.has_audio  # Pas de fichiers audio
    
    def test_debate_to_dict(self, sample_debate):
        """Test de sérialisation en dictionnaire"""
        data = sample_debate.to_dict()
        
        assert isinstance(data, dict)
        assert data["id"] == sample_debate.id
        assert data["title"] == sample_debate.title
        assert data["type"] == sample_debate.type.value
        assert data["status"] == sample_debate.status.value
        assert "created_at" in data
        assert "updated_at" in data


class TestAudioFileModel:
    """Tests du modèle AudioFile"""
    
    def test_audio_file_creation(self, sample_audio_file):
        """Test de création d'un fichier audio"""
        assert sample_audio_file.id is not None
        assert sample_audio_file.filename == "test_audio.mp3"
        assert sample_audio_file.format == "mp3"
        assert sample_audio_file.quality == "192k"
    
    def test_audio_file_properties(self, sample_audio_file):
        """Test des propriétés calculées"""
        assert sample_audio_file.is_ready
        assert not sample_audio_file.is_extracting
        assert not sample_audio_file.has_error
        assert sample_audio_file.file_size_mb == 1.0
        assert sample_audio_file.duration_formatted == "1:00:00"
    
    def test_audio_file_to_dict(self, sample_audio_file):
        """Test de sérialisation en dictionnaire"""
        data = sample_audio_file.to_dict()
        
        assert isinstance(data, dict)
        assert data["id"] == sample_audio_file.id
        assert data["filename"] == sample_audio_file.filename
        assert data["file_size_mb"] == 1.0
        assert data["is_ready"] is True


# =============================================================================
# TESTS DES SERVICES
# =============================================================================

class TestCacheService:
    """Tests du service de cache"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_cache(self):
        """Setup du cache pour les tests"""
        # Mock Redis pour les tests
        cache_service.redis_client = None
        cache_service.connected = False
        cache_service.memory_cache = {}
        yield
        # Cleanup
        cache_service.memory_cache = {}
    
    async def test_cache_set_get(self):
        """Test set/get du cache"""
        test_data = {"test": "value", "number": 42}
        
        # Set
        result = await cache_service.set("test", "key1", test_data, ttl=300)
        assert result is True
        
        # Get
        retrieved = await cache_service.get("test", "key1")
        assert retrieved == test_data
    
    async def test_cache_delete(self):
        """Test suppression du cache"""
        test_data = {"test": "value"}
        
        # Set puis delete
        await cache_service.set("test", "key1", test_data)
        result = await cache_service.delete("test", "key1")
        assert result is True
        
        # Vérifier que c'est supprimé
        retrieved = await cache_service.get("test", "key1")
        assert retrieved is None
    
    async def test_cache_namespace_clear(self):
        """Test nettoyage d'un namespace"""
        # Ajouter plusieurs clés dans le même namespace
        await cache_service.set("test", "key1", "value1")
        await cache_service.set("test", "key2", "value2")
        await cache_service.set("other", "key3", "value3")
        
        # Nettoyer le namespace "test"
        count = await cache_service.clear_namespace("test")
        assert count == 2
        
        # Vérifier que seules les clés "test" sont supprimées
        assert await cache_service.get("test", "key1") is None
        assert await cache_service.get("test", "key2") is None
        assert await cache_service.get("other", "key3") == "value3"


class TestWebSocketService:
    """Tests du service WebSocket"""
    
    async def test_websocket_stats(self):
        """Test des statistiques WebSocket"""
        stats = await websocket_manager.get_stats()
        
        assert isinstance(stats, dict)
        assert "total_connections" in stats
        assert "total_channels" in stats
        assert "channels_info" in stats
    
    async def test_websocket_message_creation(self):
        """Test de création de messages WebSocket"""
        from api.services.websocket_service import WebSocketMessage, MessageType
        
        message = WebSocketMessage(
            type=MessageType.SYSTEM_STATUS,
            channel="test",
            data={"test": "data"}
        )
        
        assert message.type == MessageType.SYSTEM_STATUS
        assert message.channel == "test"
        assert message.data == {"test": "data"}
        assert message.timestamp is not None
        assert message.message_id is not None
        
        # Test sérialisation
        message_dict = message.to_dict()
        assert isinstance(message_dict, dict)
        assert "timestamp" in message_dict
        
        message_json = message.to_json()
        assert isinstance(message_json, str)


# =============================================================================
# TESTS DE L'API
# =============================================================================

class TestMainAPI:
    """Tests de l'API principale"""
    
    async def test_root_endpoint(self, client):
        """Test du point d'entrée principal"""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "operational"
        assert "features" in data
        assert "endpoints" in data
    
    async def test_health_simple(self, client):
        """Test du health check simple"""
        response = await client.get("/health/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data


class TestDebatesAPI:
    """Tests de l'API des débats"""
    
    async def test_debates_list_empty(self, client):
        """Test de la liste des débats (vide)"""
        # Mock de la dépendance de base de données
        async def mock_get_db():
            db = AsyncMock()
            db.execute.return_value.scalars.return_value.unique.return_value.all.return_value = []
            db.execute.return_value.scalar.return_value = 0
            return db
        
        app.dependency_overrides[get_db_session] = mock_get_db
        
        try:
            response = await client.get("/api/debates/")
            assert response.status_code == 200
            
            data = response.json()
            assert "debates" in data
            assert "total" in data
            assert "page" in data
            assert "per_page" in data
            assert data["total"] == 0
            assert len(data["debates"]) == 0
        finally:
            app.dependency_overrides.clear()
    
    async def test_debates_list_with_params(self, client):
        """Test de la liste des débats avec paramètres"""
        async def mock_get_db():
            db = AsyncMock()
            db.execute.return_value.scalars.return_value.unique.return_value.all.return_value = []
            db.execute.return_value.scalar.return_value = 0
            return db
        
        app.dependency_overrides[get_db_session] = mock_get_db
        
        try:
            response = await client.get("/api/debates/?page=1&per_page=10&type=seance_publique")
            assert response.status_code == 200
            
            data = response.json()
            assert data["page"] == 1
            assert data["per_page"] == 10
        finally:
            app.dependency_overrides.clear()
    
    async def test_debate_detail_not_found(self, client):
        """Test détail d'un débat non trouvé"""
        async def mock_get_db():
            db = AsyncMock()
            db.execute.return_value.scalars.return_value.first.return_value = None
            return db
        
        app.dependency_overrides[get_db_session] = mock_get_db
        
        try:
            response = await client.get("/api/debates/nonexistent-id")
            assert response.status_code == 404
            
            data = response.json()
            assert "detail" in data
        finally:
            app.dependency_overrides.clear()


class TestStreamingAPI:
    """Tests de l'API de streaming"""
    
    async def test_streaming_info_not_found(self, client):
        """Test info streaming pour débat non trouvé"""
        async def mock_get_db():
            db = AsyncMock()
            db.execute.return_value.scalars.return_value.first.return_value = None
            return db
        
        app.dependency_overrides[get_db_session] = mock_get_db
        
        try:
            response = await client.get("/api/streaming/nonexistent-id/info")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
    
    async def test_streaming_extract_not_found(self, client):
        """Test demande d'extraction pour débat non trouvé"""
        async def mock_get_db():
            db = AsyncMock()
            db.execute.return_value.scalars.return_value.first.return_value = None
            return db
        
        app.dependency_overrides[get_db_session] = mock_get_db
        
        try:
            response = await client.post("/api/streaming/nonexistent-id/extract", json={
                "debate_id": "nonexistent-id",
                "format": "mp3",
                "quality": "192k"
            })
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


class TestCollectionsAPI:
    """Tests de l'API des collections"""
    
    async def test_collections_list_empty(self, client):
        """Test de la liste des collections (vide)"""
        async def mock_get_db():
            db = AsyncMock()
            db.execute.return_value.scalars.return_value.all.return_value = []
            return db
        
        app.dependency_overrides[get_db_session] = mock_get_db
        
        try:
            response = await client.get("/api/collections/")
            assert response.status_code == 200
            
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0
        finally:
            app.dependency_overrides.clear()
    
    async def test_favorites_list_empty(self, client):
        """Test de la liste des favoris (vide)"""
        async def mock_get_db():
            db = AsyncMock()
            db.execute.return_value.scalars.return_value.unique.return_value.all.return_value = []
            return db
        
        app.dependency_overrides[get_db_session] = mock_get_db
        
        try:
            response = await client.get("/api/favorites/")
            assert response.status_code == 200
            
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# TESTS D'INTÉGRATION
# =============================================================================

class TestIntegration:
    """Tests d'intégration"""
    
    async def test_full_api_flow(self, client):
        """Test d'un flow complet de l'API"""
        # 1. Tester la page d'accueil
        response = await client.get("/")
        assert response.status_code == 200
        
        # 2. Tester les health checks
        response = await client.get("/health/")
        assert response.status_code == 200
        
        # 3. Tester l'API des débats
        async def mock_get_db():
            db = AsyncMock()
            db.execute.return_value.scalars.return_value.unique.return_value.all.return_value = []
            db.execute.return_value.scalar.return_value = 0
            return db
        
        app.dependency_overrides[get_db_session] = mock_get_db
        
        try:
            response = await client.get("/api/debates/")
            assert response.status_code == 200
            
            # 4. Tester l'API des collections
            response = await client.get("/api/collections/")
            assert response.status_code == 200
            
            # 5. Tester l'API des favoris
            response = await client.get("/api/favorites/")
            assert response.status_code == 200
            
        finally:
            app.dependency_overrides.clear()


# =============================================================================
# TESTS DE PERFORMANCE
# =============================================================================

class TestPerformance:
    """Tests de performance basiques"""
    
    async def test_cache_performance(self):
        """Test de performance du cache"""
        import time
        
        # Test de performance pour 100 opérations
        start_time = time.time()
        
        for i in range(100):
            await cache_service.set("perf", f"key_{i}", {"data": f"value_{i}"})
        
        set_time = time.time() - start_time
        
        start_time = time.time()
        
        for i in range(100):
            value = await cache_service.get("perf", f"key_{i}")
            assert value["data"] == f"value_{i}"
        
        get_time = time.time() - start_time
        
        # Les opérations de cache doivent être rapides
        assert set_time < 1.0  # Moins d'1 seconde pour 100 SET
        assert get_time < 1.0  # Moins d'1 seconde pour 100 GET
        
        # Cleanup
        await cache_service.clear_namespace("perf")


# =============================================================================
# CONFIGURATION PYTEST
# =============================================================================

# Markers pour organiser les tests
pytest_plugins = ["pytest_asyncio"]

# Configuration des timeouts pour les tests async
pytestmark = pytest.mark.asyncio(scope="session")


if __name__ == "__main__":
    # Lancer les tests directement
    pytest.main([__file__, "-v"])
