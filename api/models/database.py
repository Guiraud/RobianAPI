"""
Configuration de base de données pour RobianAPI
SQLAlchemy 2.0 avec support async PostgreSQL
"""

import asyncio
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData, String, DateTime, Boolean, Integer, Text, JSON, Column
from sqlalchemy.sql import func
import structlog

from ..config import settings

logger = structlog.get_logger(__name__)

# Naming convention pour les contraintes
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)


Base = declarative_base(metadata=metadata)

# Mixin pour les colonnes communes
class BaseModel:
    """Mixin pour les colonnes communes"""
    id = Column(String(36), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )


# Configuration du moteur de base de données
engine = create_async_engine(
    settings.database.database_url,
    echo=settings.app.debug,  # Log SQL en mode debug
    pool_size=settings.database.db_pool_size,
    max_overflow=settings.database.db_max_overflow,
    pool_timeout=settings.database.db_pool_timeout,
    pool_recycle=3600,  # Recycler les connexions après 1h
    pool_pre_ping=True,  # Vérifier les connexions avant utilisation
)

# Session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_database():
    """Initialiser la base de données"""
    try:
        logger.info("🐘 Initialisation de la base de données PostgreSQL")
        
        # Créer toutes les tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Base de données initialisée avec succès")
        
    except Exception as e:
        logger.error("❌ Erreur initialisation base de données", error=str(e))
        raise


async def close_database():
    """Fermer les connexions à la base de données"""
    try:
        await engine.dispose()
        logger.info("🔌 Connexions base de données fermées")
    except Exception as e:
        logger.error("❌ Erreur fermeture base de données", error=str(e))


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager pour obtenir une session de base de données"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency pour FastAPI - obtenir une session de base de données"""
    async with get_session() as session:
        yield session


class DatabaseHealthCheck:
    """Service de vérification de santé de la base de données"""
    
    @staticmethod
    async def check_connection() -> dict:
        """Vérifier la connexion à la base de données"""
        try:
            async with get_session() as session:
                # Test de requête simple
                result = await session.execute(
                    "SELECT version(), current_database(), current_user, now()"
                )
                row = result.fetchone()
                
                return {
                    "status": "healthy",
                    "database": row[1] if row else "unknown",
                    "user": row[2] if row else "unknown",
                    "version": row[0].split()[1] if row and row[0] else "unknown",
                    "timestamp": row[3].isoformat() if row and row[3] else None,
                    "pool_size": engine.pool.size(),
                    "checked_out": engine.pool.checkedout(),
                }
                
        except Exception as e:
            logger.error("❌ Database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": None
            }
    
    @staticmethod
    async def check_performance() -> dict:
        """Vérifier les performances de la base de données"""
        try:
            async with get_session() as session:
                # Statistiques de performance
                queries = [
                    ("active_connections", """
                        SELECT count(*) FROM pg_stat_activity 
                        WHERE state = 'active'
                    """),
                    ("total_connections", """
                        SELECT count(*) FROM pg_stat_activity
                    """),
                    ("database_size", """
                        SELECT pg_size_pretty(pg_database_size(current_database()))
                    """),
                    ("longest_query", """
                        SELECT EXTRACT(epoch FROM (now() - query_start))::int 
                        FROM pg_stat_activity 
                        WHERE state = 'active' AND query_start IS NOT NULL
                        ORDER BY query_start DESC LIMIT 1
                    """),
                ]
                
                stats = {}
                for name, query in queries:
                    try:
                        result = await session.execute(query)
                        row = result.fetchone()
                        stats[name] = row[0] if row else None
                    except Exception:
                        stats[name] = None
                
                return {
                    "status": "healthy",
                    "performance": stats
                }
                
        except Exception as e:
            logger.error("❌ Database performance check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Utilitaires pour les migrations
async def drop_all_tables():
    """Supprimer toutes les tables (ATTENTION: destructif!)"""
    logger.warning("🚨 Suppression de toutes les tables de la base de données")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("✅ Toutes les tables supprimées")


async def create_all_tables():
    """Créer toutes les tables"""
    logger.info("🔨 Création de toutes les tables")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Toutes les tables créées")


# Export des éléments principaux
__all__ = [
    "Base",
    "engine", 
    "AsyncSessionLocal",
    "get_session",
    "get_db_session",
    "init_database",
    "close_database",
    "DatabaseHealthCheck",
    "create_all_tables",
    "drop_all_tables"
]
