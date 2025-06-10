"""
Router pour les health checks et monitoring
"""

from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import get_db_session, DatabaseHealthCheck
from ..services import cache_service, websocket_manager
from ..config import settings, get_platform_info
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check_simple():
    """Health check simple et rapide"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.app.app_version,
        "environment": settings.app.environment
    }


@router.get("/detailed")
async def health_check_detailed(db: AsyncSession = Depends(get_db_session)):
    """Health check détaillé avec vérification des services"""
    try:
        # Vérifications des services
        db_health = await DatabaseHealthCheck.check_connection()
        cache_stats = await cache_service.get_stats()
        ws_stats = await websocket_manager.get_stats()
        
        # Calcul du statut global
        overall_status = "healthy"
        if db_health["status"] != "healthy":
            overall_status = "degraded"
        if not cache_stats["redis_connected"]:
            overall_status = "degraded" if overall_status == "healthy" else "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "version": settings.app.app_version,
            "environment": settings.app.environment,
            "platform": get_platform_info(),
            "services": {
                "database": db_health,
                "cache": cache_stats,
                "websockets": ws_stats
            },
            "configuration": {
                "data_dir": str(settings.paths.data_dir),
                "cache_dir": str(settings.paths.cache_dir),
                "audio_dir": str(settings.paths.audio_dir),
                "debug": settings.app.debug
            }
        }
        
    except Exception as e:
        logger.error("❌ Erreur health check détaillé", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": "Health check failed",
                "details": str(e)
            }
        )


@router.get("/database")
async def health_check_database():
    """Health check spécifique à la base de données"""
    try:
        db_health = await DatabaseHealthCheck.check_connection()
        performance = await DatabaseHealthCheck.check_performance()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "connection": db_health,
            "performance": performance
        }
        
    except Exception as e:
        logger.error("❌ Erreur health check database", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        )


@router.get("/cache")
async def health_check_cache():
    """Health check spécifique au cache Redis"""
    try:
        cache_stats = await cache_service.get_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "cache_stats": cache_stats
        }
        
    except Exception as e:
        logger.error("❌ Erreur health check cache", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        )


@router.get("/websockets")
async def health_check_websockets():
    """Health check spécifique aux WebSockets"""
    try:
        ws_stats = await websocket_manager.get_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "websocket_stats": ws_stats
        }
        
    except Exception as e:
        logger.error("❌ Erreur health check websockets", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        )


@router.get("/metrics")
async def get_metrics():
    """Métriques Prometheus (format simple)"""
    if settings.app.environment == "production":
        return JSONResponse(
            status_code=404, 
            content={"error": "Metrics endpoint not available in production"}
        )
    
    try:
        # Statistiques de base
        db_health = await DatabaseHealthCheck.check_connection()
        cache_stats = await cache_service.get_stats()
        ws_stats = await websocket_manager.get_stats()
        
        metrics = {
            "robian_api_info": {
                "version": settings.app.app_version,
                "environment": settings.app.environment,
                "platform": get_platform_info()["system"]
            },
            "robian_api_database_healthy": 1 if db_health["status"] == "healthy" else 0,
            "robian_api_redis_connected": 1 if cache_stats["redis_connected"] else 0,
            "robian_api_websocket_connections": ws_stats["total_connections"],
            "robian_api_websocket_channels": ws_stats["total_channels"],
            "robian_api_cache_memory_size": cache_stats["memory_cache_size"],
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error("❌ Erreur récupération métriques", error=str(e))
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to collect metrics",
                "details": str(e)
            }
        )


@router.get("/readiness")
async def readiness_check():
    """
    Readiness check pour Kubernetes
    Vérifie que l'application est prête à recevoir du trafic
    """
    try:
        # Vérifications critiques pour la readiness
        db_health = await DatabaseHealthCheck.check_connection()
        
        if db_health["status"] != "healthy":
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "reason": "database_not_healthy",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "version": settings.app.app_version
        }
        
    except Exception as e:
        logger.error("❌ Erreur readiness check", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "reason": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/liveness")
async def liveness_check():
    """
    Liveness check pour Kubernetes
    Vérifie que l'application fonctionne
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "version": settings.app.app_version,
        "uptime": "N/A"  # Sera calculé plus tard si nécessaire
    }
