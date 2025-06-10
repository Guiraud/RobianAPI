"""
Service de cache Redis pour RobianAPI
Support multi-niveaux avec fallback graceful
"""

import json
import asyncio
from typing import Any, Optional, Union, Dict, List
from datetime import datetime, timedelta
import redis.asyncio as redis
from redis.exceptions import ConnectionError, TimeoutError
import pickle
import hashlib
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Service de cache Redis avec fallback mémoire"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.memory_cache: Dict[str, Dict] = {}
        self.connected = False
        self.max_memory_cache_size = 1000
        
    async def connect(self):
        """Connexion à Redis avec retry automatique"""
        try:
            self.redis_client = redis.from_url(
                settings.redis.redis_url,
                encoding="utf-8",
                decode_responses=False,  # On gère l'encoding nous-mêmes
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test de connexion
            await self.redis_client.ping()
            self.connected = True
            logger.info("✅ Connexion Redis établie")
            
        except Exception as e:
            logger.warning(f"⚠️ Échec connexion Redis: {e}. Utilisation cache mémoire.")
            self.connected = False
    
    async def disconnect(self):
        """Fermeture propre de la connexion"""
        if self.redis_client:
            await self.redis_client.close()
            self.connected = False
            logger.info("🔌 Connexion Redis fermée")
    
    def _generate_key(self, namespace: str, key: str, **kwargs) -> str:
        """Génération de clé unique avec namespace"""
        if kwargs:
            # Inclure les paramètres dans la clé
            params_str = json.dumps(kwargs, sort_keys=True)
            key_data = f"{namespace}:{key}:{params_str}"
        else:
            key_data = f"{namespace}:{key}"
        
        # Hash pour éviter les clés trop longues
        if len(key_data) > 200:
            hash_suffix = hashlib.md5(key_data.encode()).hexdigest()[:8]
            key_data = f"{namespace}:{key[:50]}...{hash_suffix}"
        
        return key_data
    
    def _serialize_value(self, value: Any) -> bytes:
        """Sérialisation robuste des valeurs"""
        try:
            # Tentative JSON d'abord (plus rapide)
            if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
                return json.dumps({
                    'type': 'json',
                    'data': value,
                    'timestamp': datetime.now().isoformat()
                }).encode()
            else:
                # Fallback pickle pour objets complexes
                return pickle.dumps({
                    'type': 'pickle',
                    'data': value,
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            logger.error(f"Erreur sérialisation: {e}")
            raise
    
    def _deserialize_value(self, data: bytes) -> Any:
        """Désérialisation robuste des valeurs"""
        try:
            # Tentative JSON d'abord
            try:
                json_data = json.loads(data.decode())
                if isinstance(json_data, dict) and 'type' in json_data:
                    return json_data['data']
                return json_data
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Fallback pickle
                pickle_data = pickle.loads(data)
                if isinstance(pickle_data, dict) and 'type' in pickle_data:
                    return pickle_data['data']
                return pickle_data
        except Exception as e:
            logger.error(f"Erreur désérialisation: {e}")
            return None
    
    async def _memory_cache_cleanup(self):
        """Nettoyage du cache mémoire si trop plein"""
        if len(self.memory_cache) > self.max_memory_cache_size:
            # Supprimer les 20% plus anciens
            sorted_items = sorted(
                self.memory_cache.items(), 
                key=lambda x: x[1].get('timestamp', 0)
            )
            
            to_remove = int(len(sorted_items) * 0.2)
            for i in range(to_remove):
                del self.memory_cache[sorted_items[i][0]]
            
            logger.debug(f"🧹 Cache mémoire nettoyé: {to_remove} items supprimés")
    
    async def set(
        self, 
        namespace: str, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None,
        **kwargs
    ) -> bool:
        """Définir une valeur en cache"""
        cache_key = self._generate_key(namespace, key, **kwargs)
        ttl = ttl or settings.redis.cache_ttl_default
        
        try:
            serialized_value = self._serialize_value(value)
            
            # Tentative Redis d'abord
            if self.connected and self.redis_client:
                try:
                    await self.redis_client.setex(cache_key, ttl, serialized_value)
                    logger.debug(f"📦 Cache Redis: {cache_key} (TTL: {ttl}s)")
                    return True
                except (ConnectionError, TimeoutError) as e:
                    logger.warning(f"⚠️ Redis indisponible: {e}")
                    self.connected = False
            
            # Fallback cache mémoire
            await self._memory_cache_cleanup()
            self.memory_cache[cache_key] = {
                'data': serialized_value,
                'timestamp': datetime.now().timestamp(),
                'expires_at': datetime.now().timestamp() + ttl
            }
            logger.debug(f"🧠 Cache mémoire: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur cache set: {e}")
            return False
    
    async def get(self, namespace: str, key: str, **kwargs) -> Optional[Any]:
        """Récupérer une valeur du cache"""
        cache_key = self._generate_key(namespace, key, **kwargs)
        
        try:
            # Tentative Redis d'abord
            if self.connected and self.redis_client:
                try:
                    data = await self.redis_client.get(cache_key)
                    if data:
                        value = self._deserialize_value(data)
                        logger.debug(f"🎯 Cache Redis hit: {cache_key}")
                        return value
                except (ConnectionError, TimeoutError) as e:
                    logger.warning(f"⚠️ Redis indisponible: {e}")
                    self.connected = False
            
            # Fallback cache mémoire
            if cache_key in self.memory_cache:
                cache_entry = self.memory_cache[cache_key]
                
                # Vérifier expiration
                if datetime.now().timestamp() > cache_entry['expires_at']:
                    del self.memory_cache[cache_key]
                    logger.debug(f"⏰ Cache mémoire expiré: {cache_key}")
                    return None
                
                value = self._deserialize_value(cache_entry['data'])
                logger.debug(f"🧠 Cache mémoire hit: {cache_key}")
                return value
            
            logger.debug(f"❌ Cache miss: {cache_key}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erreur cache get: {e}")
            return None
    
    async def delete(self, namespace: str, key: str, **kwargs) -> bool:
        """Supprimer une valeur du cache"""
        cache_key = self._generate_key(namespace, key, **kwargs)
        
        try:
            success = False
            
            # Supprimer de Redis
            if self.connected and self.redis_client:
                try:
                    result = await self.redis_client.delete(cache_key)
                    success = bool(result)
                except (ConnectionError, TimeoutError):
                    self.connected = False
            
            # Supprimer du cache mémoire
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
                success = True
            
            if success:
                logger.debug(f"🗑️ Cache supprimé: {cache_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Erreur cache delete: {e}")
            return False
    
    async def clear_namespace(self, namespace: str) -> int:
        """Supprimer tous les éléments d'un namespace"""
        try:
            count = 0
            
            # Redis
            if self.connected and self.redis_client:
                try:
                    pattern = f"{namespace}:*"
                    keys = await self.redis_client.keys(pattern)
                    if keys:
                        count += await self.redis_client.delete(*keys)
                except (ConnectionError, TimeoutError):
                    self.connected = False
            
            # Cache mémoire
            keys_to_delete = [k for k in self.memory_cache.keys() if k.startswith(f"{namespace}:")]
            for key in keys_to_delete:
                del self.memory_cache[key]
                count += 1
            
            logger.info(f"🧹 Namespace {namespace} nettoyé: {count} items")
            return count
            
        except Exception as e:
            logger.error(f"❌ Erreur clear namespace: {e}")
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Statistiques du cache"""
        stats = {
            'redis_connected': self.connected,
            'memory_cache_size': len(self.memory_cache),
            'memory_cache_max_size': self.max_memory_cache_size,
        }
        
        if self.connected and self.redis_client:
            try:
                redis_info = await self.redis_client.info()
                stats.update({
                    'redis_used_memory': redis_info.get('used_memory_human'),
                    'redis_connected_clients': redis_info.get('connected_clients'),
                    'redis_keyspace_hits': redis_info.get('keyspace_hits'),
                    'redis_keyspace_misses': redis_info.get('keyspace_misses'),
                })
            except Exception:
                pass
        
        return stats


# Instance globale du service de cache
cache_service = CacheService()


# Fonctions de convenance pour les différents types de cache
async def cache_debates(key: str, value: Any, **kwargs) -> bool:
    """Cache spécifique pour les débats"""
    return await cache_service.set(
        "debates", key, value, 
        ttl=settings.redis.cache_ttl_debates, 
        **kwargs
    )


async def get_cached_debates(key: str, **kwargs) -> Optional[Any]:
    """Récupération cache débats"""
    return await cache_service.get("debates", key, **kwargs)


async def cache_streaming(key: str, value: Any, **kwargs) -> bool:
    """Cache spécifique pour le streaming"""
    return await cache_service.set(
        "streaming", key, value,
        ttl=settings.redis.cache_ttl_streaming,
        **kwargs
    )


async def get_cached_streaming(key: str, **kwargs) -> Optional[Any]:
    """Récupération cache streaming"""
    return await cache_service.get("streaming", key, **kwargs)


async def cache_metadata(key: str, value: Any, **kwargs) -> bool:
    """Cache spécifique pour les métadonnées"""
    return await cache_service.set(
        "metadata", key, value,
        ttl=settings.redis.cache_ttl_metadata,
        **kwargs
    )


async def get_cached_metadata(key: str, **kwargs) -> Optional[Any]:
    """Récupération cache métadonnées"""
    return await cache_service.get("metadata", key, **kwargs)


# Décorateur pour mise en cache automatique
def cached(namespace: str, ttl: Optional[int] = None, key_func=None):
    """Décorateur pour mise en cache automatique des fonctions"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Génération de la clé
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}_{hash((args, tuple(sorted(kwargs.items()))))}"
            
            # Tentative de récupération du cache
            cached_result = await cache_service.get(namespace, cache_key)
            if cached_result is not None:
                return cached_result
            
            # Exécution de la fonction et mise en cache
            result = await func(*args, **kwargs)
            await cache_service.set(namespace, cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator
