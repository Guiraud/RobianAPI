"""
Point d'entrée principal modernisé pour RobianAPI
Intégration de tous les services : Cache Redis, WebSockets, PostgreSQL
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any
from datetime import datetime

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import structlog

from .config import settings, get_platform_info
from .middleware import setup_middleware, global_exception_handler
from .models import init_database, close_database, DatabaseHealthCheck
from .services.cache_service import cache_service
from .services.websocket_service import websocket_manager, WebSocketMessage, MessageType

# Import des routers
from .routers import (
    debates_router,
    streaming_router,
    collections_router,
    health_router
)

# Configuration du logger
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire du cycle de vie de l'application"""
    logger.info("🚀 Démarrage RobianAPI", version=settings.app.app_version)
    
    try:
        # 1. Initialisation de la base de données
        logger.info("🐘 Initialisation PostgreSQL...")
        await init_database()
        
        # 2. Connexion au cache Redis
        logger.info("🔴 Connexion Redis...")
        await cache_service.connect()
        
        # 3. Vérifications système
        platform_info = get_platform_info()
        logger.info("💻 Plateforme détectée", 
                   system=platform_info["system"],
                   python_version=platform_info["python_version"])
        
        # 4. Affichage de la configuration
        logger.info("⚙️ Configuration chargée",
                   environment=settings.app.environment,
                   debug=settings.app.debug,
                   data_dir=str(settings.paths.data_dir))
        
        logger.info("✅ RobianAPI initialisée avec succès")
        
        yield  # L'application fonctionne ici
        
    except Exception as e:
        logger.error("❌ Erreur lors de l'initialisation", error=str(e))
        raise
    
    finally:
        # Nettoyage lors de l'arrêt
        logger.info("🛑 Arrêt de RobianAPI...")
        
        try:
            await cache_service.disconnect()
            await close_database()
            logger.info("✅ Nettoyage terminé")
        except Exception as e:
            logger.error("❌ Erreur lors du nettoyage", error=str(e))


# Création de l'application FastAPI
app = FastAPI(
    title=settings.app.app_name,
    description=settings.app.app_description,
    version=settings.app.app_version,
    docs_url=settings.app.docs_url if settings.app.environment != "production" else None,
    redoc_url=settings.app.redoc_url if settings.app.environment != "production" else None,
    openapi_url=settings.app.openapi_url if settings.app.environment != "production" else None,
    lifespan=lifespan
)

# Configuration des middlewares
setup_middleware(app)

# Handler d'exceptions global
app.add_exception_handler(Exception, global_exception_handler)

# Inclusion des routers
app.include_router(health_router)
app.include_router(debates_router)
app.include_router(streaming_router)
app.include_router(collections_router)


# =============================================================================
# ROUTES PRINCIPALES
# =============================================================================

@app.get("/", response_model=Dict[str, Any])
async def root():
    """Point d'entrée principal de l'API"""
    return {
        "message": "RobianAPI - API Backend pour l'application RobianAPP",
        "version": settings.app.app_version,
        "environment": settings.app.environment,
        "status": "operational",
        "features": {
            "cache_redis": True,
            "websockets": True,
            "database": "postgresql",
            "platform": get_platform_info()["system"]
        },
        "endpoints": {
            "debates": "/api/debates/",
            "streaming": "/api/streaming/",
            "collections": "/api/collections/",
            "favorites": "/api/favorites/",
            "websocket": "/ws",
            "health": "/health/",
            "docs": settings.app.docs_url if settings.app.environment != "production" else None
        },
        "links": {
            "documentation": settings.app.docs_url if settings.app.environment != "production" else None,
            "repository": "https://github.com/robian-api/robian-api",
            "support": "https://github.com/robian-api/robian-api/issues"
        }
    }


# =============================================================================
# WEBSOCKET ENDPOINT
# =============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    """Endpoint WebSocket pour les notifications temps réel"""
    client_id = await websocket_manager.connect(websocket, client_id)
    
    try:
        while True:
            # Recevoir et traiter les messages du client
            message = await websocket.receive_text()
            await websocket_manager.handle_message(client_id, message)
            
    except WebSocketDisconnect:
        await websocket_manager.disconnect(client_id)
        logger.info("🔌 Client WebSocket déconnecté", client_id=client_id)
    except Exception as e:
        logger.error("❌ Erreur WebSocket", client_id=client_id, error=str(e))
        await websocket_manager.disconnect(client_id)


# =============================================================================
# ROUTES DE COMPATIBILITÉ (anciennes routes)
# =============================================================================

@app.get("/api/debats")
async def legacy_list_debates(
    date_debut: str = None,
    date_fin: str = None,
    type_debat: str = None,
    commission: str = None,
    limit: int = 50
):
    """
    Route de compatibilité pour l'ancienne API
    Redirige vers la nouvelle API moderne avec cache
    """
    # Redirection vers le router des débats
    from .routers.debates import list_debates
    from .models import get_db_session
    
    # Simuler les paramètres pour la nouvelle API
    filters = {}
    if type_debat:
        filters["type"] = type_debat
    if commission:
        filters["commission"] = commission
    
    # Note: Cette redirection simple ne gère pas parfaitement tous les cas
    # En production, utiliser une vraie redirection HTTP ou adapter les paramètres
    return {
        "message": "Cette route est dépréciée. Utilisez /api/debates/ à la place.",
        "new_endpoint": "/api/debates/",
        "filters_suggested": filters
    }


@app.get("/api/debats/{debat_id}")
async def legacy_get_debate(debat_id: str):
    """Route de compatibilité pour l'ancienne API"""
    return {
        "message": "Cette route est dépréciée. Utilisez /api/debates/{debate_id} à la place.",
        "new_endpoint": f"/api/debates/{debat_id}"
    }


@app.get("/api/programme")
async def legacy_programme(date_param: str = None):
    """Route de compatibilité pour le programme"""
    target_date = date_param or datetime.now().strftime('%Y-%m-%d')
    
    # Cache check
    cache_key = f"programme_{target_date}"
    cached_programme = await cache_service.get("metadata", cache_key)
    if cached_programme:
        return cached_programme
    
    # Simulation du programme (à remplacer par DB query des ScheduledSession)
    programme = [
        {
            "date": target_date,
            "heure": "09:00",
            "titre": "Séance publique",
            "type": "seance_publique",
            "commission": None,
            "salle": "Hémicycle",
            "url": "https://videos.assemblee-nationale.fr/live"
        },
        {
            "date": target_date,
            "heure": "14:00",
            "titre": "Commission des finances",
            "type": "commission",
            "commission": "Finances",
            "salle": "Salle 6350",
            "url": None
        }
    ]
    
    # Cache pour 24h (programme change peu)
    await cache_service.set("metadata", cache_key, programme, ttl=86400)
    
    return programme


@app.get("/api/cache/stats")
async def cache_stats():
    """Statistiques du cache Redis (debug)"""
    if settings.app.environment == "production":
        return JSONResponse(status_code=404, content={"error": "Not available in production"})
    
    stats = await cache_service.get_stats()
    return {
        "cache_stats": stats,
        "websocket_stats": await websocket_manager.get_stats()
    }


# =============================================================================
# ROUTES D'EXTRACTION (compatibilité)
# =============================================================================

@app.post("/api/extraction")
async def legacy_extraction_request(request: Request):
    """Route de compatibilité pour l'extraction"""
    body = await request.json()
    debate_id = body.get("debate_id")
    
    if not debate_id:
        return JSONResponse(
            status_code=400,
            content={"error": "debate_id requis"}
        )
    
    return {
        "message": "Cette route est dépréciée. Utilisez /api/streaming/{debate_id}/extract à la place.",
        "new_endpoint": f"/api/streaming/{debate_id}/extract",
        "method": "POST"
    }


@app.get("/api/extraction/{extraction_id}")
async def legacy_extraction_status(extraction_id: str):
    """Route de compatibilité pour le statut d'extraction"""
    return {
        "message": "Cette route est dépréciée. Utilisez /api/streaming/{debate_id}/status à la place.",
        "extraction_id": extraction_id
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Démarrage direct de RobianAPI")
    uvicorn.run(
        "api.main:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.reload,
        log_level=settings.monitoring.log_level.lower()
    )
