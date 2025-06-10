"""
Middleware pour RobianAPI
CORS, Rate Limiting, Logging, Sécurité
"""

import time
import logging
import json
from typing import Callable, Dict, Any
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict, deque

from fastapi import Request, Response, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware as StarletteBaseMiddleware
from starlette.responses import JSONResponse
import structlog

from ..config import settings

# Configuration du logging structuré
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.monitoring.log_format == "json" 
        else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware de logging des requêtes"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Début de la requête
        start_time = time.time()
        request_id = f"req_{int(time.time() * 1000000)}"
        
        # Informations de la requête
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Logger de début
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "client_ip": client_ip,
            "user_agent": user_agent,
            "headers": dict(request.headers) if settings.app.debug else {},
        }
        
        logger.info("Request started", **log_data)
        
        # Ajouter l'ID de requête au contexte
        request.state.request_id = request_id
        
        try:
            # Traitement de la requête
            response = await call_next(request)
            
            # Calculer la durée
            process_time = time.time() - start_time
            
            # Logger de fin
            log_data.update({
                "status_code": response.status_code,
                "process_time": round(process_time, 4),
                "response_size": response.headers.get("content-length", "unknown"),
            })
            
            # Niveau de log selon le status code
            if response.status_code >= 500:
                logger.error("Request completed with server error", **log_data)
            elif response.status_code >= 400:
                logger.warning("Request completed with client error", **log_data)
            else:
                logger.info("Request completed successfully", **log_data)
            
            # Ajouter headers de debug
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Calculer la durée même en cas d'erreur
            process_time = time.time() - start_time
            
            log_data.update({
                "error": str(e),
                "error_type": type(e).__name__,
                "process_time": round(process_time, 4),
            })
            
            logger.error("Request failed with exception", **log_data)
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Obtenir l'IP réelle du client (gestion des proxies)"""
        # Ordre de priorité pour les headers de proxy
        ip_headers = [
            "CF-Connecting-IP",      # Cloudflare
            "X-Forwarded-For",       # Standard proxy
            "X-Real-IP",             # Nginx
            "X-Client-IP",           # Apache
        ]
        
        for header in ip_headers:
            ip = request.headers.get(header)
            if ip:
                # Prendre la première IP si multiple (X-Forwarded-For peut en avoir plusieurs)
                return ip.split(",")[0].strip()
        
        # Fallback sur l'IP de connexion directe
        return request.client.host if request.client else "unknown"


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware de rate limiting"""
    
    def __init__(self, app):
        super().__init__(app)
        # Stockage en mémoire pour le rate limiting
        # En production, utiliser Redis pour partage entre instances
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.blocked_ips: Dict[str, datetime] = {}
        
        # Configuration
        self.requests_per_minute = settings.security.rate_limit_per_minute
        self.burst_limit = settings.security.rate_limit_burst
        self.block_duration = timedelta(minutes=10)  # Blocage temporaire
        
        # Task de nettoyage
        self.cleanup_task = asyncio.create_task(self._cleanup_old_requests())
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Obtenir l'IP du client
        client_ip = self._get_client_ip(request)
        
        # Vérifier si l'IP est bloquée
        if self._is_ip_blocked(client_ip):
            logger.warning("Request blocked - IP temporarily banned", 
                         client_ip=client_ip, url=str(request.url))
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "message": "Your IP has been temporarily blocked due to excessive requests",
                    "retry_after": "10 minutes"
                },
                headers={"Retry-After": "600"}
            )
        
        # Vérifier le rate limit
        if not self._check_rate_limit(client_ip, request):
            logger.warning("Request rate limited", 
                         client_ip=client_ip, url=str(request.url))
            
            # Bloquer l'IP si trop de violations
            violations = self._count_recent_violations(client_ip)
            if violations > 5:  # 5 violations en 1 minute = blocage
                self._block_ip(client_ip)
                logger.warning("IP blocked for excessive rate limit violations", 
                             client_ip=client_ip)
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute allowed",
                    "retry_after": "60 seconds"
                },
                headers={"Retry-After": "60"}
            )
        
        # Enregistrer la requête
        self._record_request(client_ip)
        
        # Continuer le traitement
        response = await call_next(request)
        
        # Ajouter headers de rate limiting
        remaining = self._get_remaining_requests(client_ip)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Même logique que RequestLoggingMiddleware"""
        ip_headers = ["CF-Connecting-IP", "X-Forwarded-For", "X-Real-IP", "X-Client-IP"]
        
        for header in ip_headers:
            ip = request.headers.get(header)
            if ip:
                return ip.split(",")[0].strip()
        
        return request.client.host if request.client else "unknown"
    
    def _check_rate_limit(self, client_ip: str, request: Request) -> bool:
        """Vérifier si la requête respecte le rate limit"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Nettoyer les anciennes requêtes
        while self.requests[client_ip] and self.requests[client_ip][0] < minute_ago:
            self.requests[client_ip].popleft()
        
        # Rate limit différent selon le endpoint
        endpoint_limits = {
            "/api/extraction": 10,      # Extraction limitée
            "/api/debats": 60,          # Débats plus permissif
            "/health": 200,             # Health checks fréquents OK
        }
        
        # Déterminer la limite pour cet endpoint
        path = request.url.path
        limit = endpoint_limits.get(path, self.requests_per_minute)
        
        # Vérifier le burst limit aussi
        recent_requests = len([r for r in self.requests[client_ip] if r > now - timedelta(seconds=10)])
        if recent_requests > self.burst_limit:
            return False
        
        # Vérifier la limite par minute
        return len(self.requests[client_ip]) < limit
    
    def _record_request(self, client_ip: str):
        """Enregistrer une requête"""
        self.requests[client_ip].append(datetime.now())
    
    def _get_remaining_requests(self, client_ip: str) -> int:
        """Obtenir le nombre de requêtes restantes"""
        return max(0, self.requests_per_minute - len(self.requests[client_ip]))
    
    def _is_ip_blocked(self, client_ip: str) -> bool:
        """Vérifier si une IP est bloquée"""
        if client_ip in self.blocked_ips:
            if datetime.now() - self.blocked_ips[client_ip] > self.block_duration:
                # Débloquer l'IP
                del self.blocked_ips[client_ip]
                return False
            return True
        return False
    
    def _block_ip(self, client_ip: str):
        """Bloquer une IP temporairement"""
        self.blocked_ips[client_ip] = datetime.now()
    
    def _count_recent_violations(self, client_ip: str) -> int:
        """Compter les violations récentes de rate limit"""
        # Pour simplifier, on considère le nombre de requêtes récentes
        now = datetime.now()
        recent = now - timedelta(minutes=1)
        return len([r for r in self.requests[client_ip] if r > recent])
    
    async def _cleanup_old_requests(self):
        """Task de nettoyage des anciennes requêtes"""
        while True:
            try:
                await asyncio.sleep(300)  # Nettoyage toutes les 5 minutes
                
                now = datetime.now()
                hour_ago = now - timedelta(hours=1)
                
                # Nettoyer les anciennes requêtes
                for client_ip in list(self.requests.keys()):
                    while self.requests[client_ip] and self.requests[client_ip][0] < hour_ago:
                        self.requests[client_ip].popleft()
                    
                    # Supprimer les entrées vides
                    if not self.requests[client_ip]:
                        del self.requests[client_ip]
                
                # Nettoyer les IPs bloquées expirées
                expired_blocks = [
                    ip for ip, blocked_at in self.blocked_ips.items()
                    if now - blocked_at > self.block_duration
                ]
                for ip in expired_blocks:
                    del self.blocked_ips[ip]
                
                if expired_blocks:
                    logger.info(f"Cleaned up {len(expired_blocks)} expired IP blocks")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in rate limiting cleanup", error=str(e))


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware pour ajouter des headers de sécurité"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Headers de sécurité
        security_headers = {
            # Prévention XSS
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            
            # HSTS (uniquement en HTTPS)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains" 
            if request.url.scheme == "https" else None,
            
            # CSP basique
            "Content-Security-Policy": 
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' ws: wss:;",
            
            # Permissions Policy
            "Permissions-Policy": 
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()",
            
            # Referrer Policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Server info (masquer la version)
            "Server": "RobianAPI/1.0",
        }
        
        # Ajouter les headers (sauf None)
        for header, value in security_headers.items():
            if value is not None:
                response.headers[header] = value
        
        return response


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """Middleware pour bypass rapide des health checks"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Bypass rapide pour les health checks
        if request.url.path in ["/health", "/health/"]:
            return JSONResponse(
                content={
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "version": settings.app.app_version
                },
                headers={"Cache-Control": "no-cache"}
            )
        
        return await call_next(request)


def setup_cors_middleware(app):
    """Configuration du middleware CORS"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.backend_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Request-ID",
            "Cache-Control",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-Process-Time",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ]
    )


def setup_middleware(app):
    """Configuration de tous les middlewares"""
    
    # 1. Health check (le plus rapide, en premier)
    app.add_middleware(HealthCheckMiddleware)
    
    # 2. Sécurité headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 3. Rate limiting (avant logging pour éviter de logger les requêtes bloquées)
    if settings.security.rate_limit_per_minute > 0:
        app.add_middleware(RateLimitingMiddleware)
    
    # 4. Logging des requêtes
    app.add_middleware(RequestLoggingMiddleware)
    
    # 5. CORS (en dernier pour gérer les preflight OPTIONS)
    setup_cors_middleware(app)
    
    logger.info("Middleware stack configured", 
                rate_limiting=settings.security.rate_limit_per_minute > 0,
                cors_origins=len(settings.security.backend_cors_origins),
                log_format=settings.monitoring.log_format)


# Classes d'exception personnalisées
class RobianAPIException(HTTPException):
    """Exception de base pour RobianAPI"""
    
    def __init__(
        self, 
        status_code: int, 
        message: str, 
        details: Dict[str, Any] = None,
        error_code: str = None
    ):
        self.message = message
        self.details = details or {}
        self.error_code = error_code
        
        super().__init__(
            status_code=status_code,
            detail={
                "error": message,
                "error_code": error_code,
                "details": self.details,
                "timestamp": datetime.now().isoformat()
            }
        )


class ValidationError(RobianAPIException):
    """Erreur de validation des données"""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["invalid_value"] = str(value)
        
        super().__init__(
            status_code=422,
            message=message,
            details=details,
            error_code="VALIDATION_ERROR"
        )


class ResourceNotFoundError(RobianAPIException):
    """Ressource non trouvée"""
    
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            status_code=404,
            message=f"{resource_type} not found",
            details={"resource_type": resource_type, "resource_id": resource_id},
            error_code="RESOURCE_NOT_FOUND"
        )


class ExtractionError(RobianAPIException):
    """Erreur d'extraction audio"""
    
    def __init__(self, message: str, url: str = None, stage: str = None):
        details = {}
        if url:
            details["url"] = url
        if stage:
            details["stage"] = stage
        
        super().__init__(
            status_code=500,
            message=f"Audio extraction failed: {message}",
            details=details,
            error_code="EXTRACTION_ERROR"
        )


class CacheError(RobianAPIException):
    """Erreur de cache"""
    
    def __init__(self, message: str, cache_key: str = None):
        details = {}
        if cache_key:
            details["cache_key"] = cache_key
        
        super().__init__(
            status_code=500,
            message=f"Cache error: {message}",
            details=details,
            error_code="CACHE_ERROR"
        )


# Handler d'exceptions global
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler global pour toutes les exceptions non gérées"""
    
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    if isinstance(exc, RobianAPIException):
        # Exception métier déjà formatée
        logger.warning("Business exception occurred", 
                      request_id=request_id,
                      error_code=exc.error_code,
                      message=exc.message,
                      details=exc.details)
        
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    elif isinstance(exc, HTTPException):
        # Exception HTTP standard
        logger.warning("HTTP exception occurred",
                      request_id=request_id,
                      status_code=exc.status_code,
                      detail=exc.detail)
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id
            }
        )
    
    else:
        # Exception non gérée
        logger.error("Unhandled exception occurred",
                    request_id=request_id,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    exc_info=True)
        
        # En production, ne pas exposer les détails internes
        if settings.app.environment == "production":
            error_detail = "Internal server error"
        else:
            error_detail = f"{type(exc).__name__}: {str(exc)}"
        
        return JSONResponse(
            status_code=500,
            content={
                "error": error_detail,
                "error_code": "INTERNAL_ERROR",
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id
            }
        )
