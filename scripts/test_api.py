#!/usr/bin/env python3
"""
Script de test et validation RobianAPI
Tests de l'API, de la base de données et des services
"""

import asyncio
import sys
import httpx
import json
from pathlib import Path

# Ajouter le dossier parent au PYTHONPATH pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.config import settings
from api.models import DatabaseHealthCheck, close_database
from api.services import cache_service, websocket_manager
import structlog

logger = structlog.get_logger(__name__)


class RobianAPITester:
    """Classe principale de test de l'API"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or f"http://{settings.app.host}:{settings.app.port}"
        self.client = None
        self.test_results = []
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    def log_test_result(self, test_name: str, success: bool, details: str = None):
        """Enregistrer le résultat d'un test"""
        result = {
            "test": test_name,
            "success": success,
            "details": details
        }
        self.test_results.append(result)
        
        if success:
            logger.info(f"✅ {test_name}", details=details)
        else:
            logger.error(f"❌ {test_name}", details=details)
    
    async def test_api_root(self):
        """Test du point d'entrée de l'API"""
        try:
            response = await self.client.get("/")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "version" in data:
                    self.log_test_result("API Root", True, f"Version: {data['version']}")
                else:
                    self.log_test_result("API Root", False, "Réponse manque des champs requis")
            else:
                self.log_test_result("API Root", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("API Root", False, str(e))
    
    async def test_health_checks(self):
        """Test des health checks"""
        health_endpoints = [
            "/health/",
            "/health/detailed",
            "/health/database",
            "/health/cache",
            "/health/websockets"
        ]
        
        for endpoint in health_endpoints:
            try:
                response = await self.client.get(endpoint)
                
                if response.status_code in [200, 503]:  # 503 acceptable pour des services down
                    data = response.json()
                    status = data.get("status", "unknown")
                    self.log_test_result(f"Health Check {endpoint}", True, f"Status: {status}")
                else:
                    self.log_test_result(f"Health Check {endpoint}", False, f"Status: {response.status_code}")
                    
            except Exception as e:
                self.log_test_result(f"Health Check {endpoint}", False, str(e))
    
    async def test_debates_api(self):
        """Test de l'API des débats"""
        try:
            # Test liste des débats
            response = await self.client.get("/api/debates/")
            
            if response.status_code == 200:
                data = response.json()
                if "debates" in data and "total" in data:
                    debates_count = len(data["debates"])
                    total = data["total"]
                    self.log_test_result("Debates List", True, f"{debates_count} débats sur {total}")
                    
                    # Test détail d'un débat si disponible
                    if debates_count > 0:
                        first_debate_id = data["debates"][0]["id"]
                        await self.test_debate_detail(first_debate_id)
                else:
                    self.log_test_result("Debates List", False, "Format de réponse invalide")
            else:
                self.log_test_result("Debates List", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("Debates List", False, str(e))
    
    async def test_debate_detail(self, debate_id: str):
        """Test du détail d'un débat"""
        try:
            response = await self.client.get(f"/api/debates/{debate_id}")
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "title" in data:
                    self.log_test_result("Debate Detail", True, f"Débat: {data['title'][:50]}...")
                else:
                    self.log_test_result("Debate Detail", False, "Format de réponse invalide")
            elif response.status_code == 404:
                self.log_test_result("Debate Detail", True, "Débat non trouvé (attendu)")
            else:
                self.log_test_result("Debate Detail", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("Debate Detail", False, str(e))
    
    async def test_streaming_api(self):
        """Test de l'API de streaming"""
        try:
            # D'abord récupérer un débat
            debates_response = await self.client.get("/api/debates/?per_page=1")
            
            if debates_response.status_code == 200:
                debates_data = debates_response.json()
                if debates_data["debates"]:
                    debate_id = debates_data["debates"][0]["id"]
                    
                    # Test info streaming
                    info_response = await self.client.get(f"/api/streaming/{debate_id}/info")
                    
                    if info_response.status_code == 200:
                        info_data = info_response.json()
                        audio_available = info_data.get("audio_available", False)
                        self.log_test_result("Streaming Info", True, 
                                           f"Audio disponible: {audio_available}")
                        
                        # Si audio disponible, tester le streaming
                        if audio_available:
                            await self.test_audio_streaming(debate_id)
                    else:
                        self.log_test_result("Streaming Info", False, 
                                           f"Status: {info_response.status_code}")
                else:
                    self.log_test_result("Streaming Info", False, "Aucun débat disponible pour test")
            else:
                self.log_test_result("Streaming Info", False, "Impossible de récupérer les débats")
                
        except Exception as e:
            self.log_test_result("Streaming Info", False, str(e))
    
    async def test_audio_streaming(self, debate_id: str):
        """Test du streaming audio"""
        try:
            # Test endpoint stream avec HEAD request pour éviter de télécharger
            response = await self.client.head(f"/api/streaming/{debate_id}/stream")
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "audio" in content_type:
                    self.log_test_result("Audio Streaming", True, f"Content-Type: {content_type}")
                else:
                    self.log_test_result("Audio Streaming", False, f"Content-Type invalide: {content_type}")
            elif response.status_code == 404:
                self.log_test_result("Audio Streaming", True, "Fichier audio non trouvé (attendu)")
            else:
                self.log_test_result("Audio Streaming", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("Audio Streaming", False, str(e))
    
    async def test_collections_api(self):
        """Test de l'API des collections"""
        try:
            # Test liste des collections
            response = await self.client.get("/api/collections/")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    collections_count = len(data)
                    self.log_test_result("Collections List", True, f"{collections_count} collections")
                else:
                    self.log_test_result("Collections List", False, "Format de réponse invalide")
            else:
                self.log_test_result("Collections List", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("Collections List", False, str(e))
    
    async def test_favorites_api(self):
        """Test de l'API des favoris"""
        try:
            # Test liste des favoris (sans user_id, devrait retourner liste vide)
            response = await self.client.get("/api/favorites/")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test_result("Favorites List", True, f"{len(data)} favoris")
                else:
                    self.log_test_result("Favorites List", False, "Format de réponse invalide")
            else:
                self.log_test_result("Favorites List", False, f"Status: {response.status_code}")
                
        except Exception as e:
            self.log_test_result("Favorites List", False, str(e))
    
    async def run_all_tests(self):
        """Exécuter tous les tests"""
        logger.info("🧪 Démarrage des tests RobianAPI")
        
        test_methods = [
            self.test_api_root,
            self.test_health_checks,
            self.test_debates_api,
            self.test_streaming_api,
            self.test_collections_api,
            self.test_favorites_api
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                logger.error(f"❌ Erreur durant {test_method.__name__}", error=str(e))
        
        # Résumé des tests
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - successful_tests
        
        logger.info("📊 Résumé des tests:")
        logger.info(f"   ✅ Réussis: {successful_tests}")
        logger.info(f"   ❌ Échoués: {failed_tests}")
        logger.info(f"   📊 Total: {total_tests}")
        
        if failed_tests > 0:
            logger.info("❌ Tests échoués:")
            for result in self.test_results:
                if not result["success"]:
                    logger.info(f"   - {result['test']}: {result['details']}")
        
        return failed_tests == 0


async def test_database_directly():
    """Test direct de la base de données"""
    logger.info("🔍 Test direct de la base de données")
    
    try:
        # Health check
        health = await DatabaseHealthCheck.check_connection()
        if health["status"] == "healthy":
            logger.info("✅ Connexion base de données OK")
        else:
            logger.error("❌ Connexion base de données KO", health=health)
            return False
        
        # Performance check
        performance = await DatabaseHealthCheck.check_performance()
        if performance["status"] == "healthy":
            logger.info("✅ Performance base de données OK", stats=performance.get("performance", {}))
        else:
            logger.error("❌ Performance base de données KO", performance=performance)
        
        return True
        
    except Exception as e:
        logger.error("❌ Erreur test base de données", error=str(e))
        return False
    
    finally:
        await close_database()


async def test_cache_directly():
    """Test direct du cache Redis"""
    logger.info("🔍 Test direct du cache Redis")
    
    try:
        # Connexion
        await cache_service.connect()
        
        # Test set/get
        test_key = "test_key"
        test_value = {"test": "value", "timestamp": "2025-06-09"}
        
        # Set
        set_result = await cache_service.set("test", test_key, test_value, ttl=60)
        if set_result:
            logger.info("✅ Cache SET OK")
        else:
            logger.error("❌ Cache SET échoué")
            return False
        
        # Get
        get_result = await cache_service.get("test", test_key)
        if get_result == test_value:
            logger.info("✅ Cache GET OK")
        else:
            logger.error("❌ Cache GET échoué", expected=test_value, got=get_result)
            return False
        
        # Delete
        delete_result = await cache_service.delete("test", test_key)
        if delete_result:
            logger.info("✅ Cache DELETE OK")
        else:
            logger.error("❌ Cache DELETE échoué")
        
        # Stats
        stats = await cache_service.get_stats()
        logger.info("📊 Stats cache", **stats)
        
        return True
        
    except Exception as e:
        logger.error("❌ Erreur test cache", error=str(e))
        return False
    
    finally:
        await cache_service.disconnect()


async def test_websockets_directly():
    """Test direct des WebSockets"""
    logger.info("🔍 Test direct des WebSockets")
    
    try:
        # Stats WebSocket
        stats = await websocket_manager.get_stats()
        logger.info("📊 Stats WebSocket", **stats)
        
        # Test envoi message (même si pas de connexions)
        from api.services.websocket_service import WebSocketMessage, MessageType
        
        test_message = WebSocketMessage(
            type=MessageType.SYSTEM_STATUS,
            channel="test",
            data={"test": "message"}
        )
        
        # Ceci n'enverra rien car pas de connexions, mais ne doit pas planter
        await websocket_manager.broadcast_to_channel("test", test_message)
        
        logger.info("✅ WebSockets manager OK")
        return True
        
    except Exception as e:
        logger.error("❌ Erreur test WebSockets", error=str(e))
        return False


async def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Tests RobianAPI")
    parser.add_argument(
        "--api-only", 
        action="store_true",
        help="Tester uniquement l'API (pas les services directs)"
    )
    parser.add_argument(
        "--services-only", 
        action="store_true",
        help="Tester uniquement les services directs (pas l'API)"
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="URL de base de l'API à tester"
    )
    
    args = parser.parse_args()
    
    # Configurer le logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger.info("🧪 RobianAPI Test Suite")
    logger.info(f"   Environnement: {settings.app.environment}")
    
    all_success = True
    
    # Tests des services directs
    if not args.api_only:
        logger.info("🔧 Tests des services directs")
        
        db_success = await test_database_directly()
        cache_success = await test_cache_directly()
        ws_success = await test_websockets_directly()
        
        if not (db_success and cache_success and ws_success):
            all_success = False
            logger.error("❌ Certains services ont échoué")
    
    # Tests de l'API
    if not args.services_only:
        logger.info("🌐 Tests de l'API")
        
        async with RobianAPITester(args.base_url) as tester:
            api_success = await tester.run_all_tests()
            
            if not api_success:
                all_success = False
    
    # Résultat final
    if all_success:
        logger.info("🎉 Tous les tests sont passés avec succès!")
        sys.exit(0)
    else:
        logger.error("💥 Certains tests ont échoué")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
