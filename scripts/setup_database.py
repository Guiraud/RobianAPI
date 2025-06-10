#!/usr/bin/env python3
"""
Script de setup et gestion de la base de données RobianAPI
"""

import asyncio
import sys
from pathlib import Path

# Ajouter le dossier parent au PYTHONPATH pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.models import (
    init_database, 
    close_database, 
    create_all_tables, 
    drop_all_tables,
    DatabaseHealthCheck
)
from api.config import settings
import structlog

logger = structlog.get_logger(__name__)


async def setup_database():
    """
    Initialiser la base de données avec toutes les tables
    """
    
    try:
        logger.info("🔨 Setup de la base de données")
        logger.info("📋 Configuration:", 
                   database_url=settings.database.database_url,
                   environment=settings.app.environment)
        
        # Initialiser la base de données
        await init_database()
        
        # Vérifier la connexion
        health = await DatabaseHealthCheck.check_connection()
        if health["status"] != "healthy":
            raise Exception(f"Database health check failed: {health}")
        
        logger.info("✅ Base de données initialisée avec succès")
        logger.info("📊 Informations:", 
                   database=health.get("database"),
                   version=health.get("version"),
                   user=health.get("user"))
        
        return True
        
    except Exception as e:
        logger.error("❌ Erreur setup base de données", error=str(e))
        return False
    
    finally:
        await close_database()


async def reset_database():
    """
    Supprimer et recréer toutes les tables (ATTENTION: destructeur!)
    """
    
    if settings.app.environment == "production":
        logger.error("❌ Reset de base de données interdit en production!")
        return False
    
    try:
        logger.warning("🚨 RESET de la base de données - TOUTES les données seront perdues!")
        
        # Confirmation en mode interactif
        if sys.stdin.isatty():
            confirm = input("Êtes-vous sûr? Tapez 'YES' pour confirmer: ")
            if confirm != "YES":
                logger.info("❌ Reset annulé")
                return False
        
        logger.info("🗑️ Suppression de toutes les tables...")
        await drop_all_tables()
        
        logger.info("🔨 Recréation de toutes les tables...")
        await create_all_tables()
        
        # Vérifier que tout fonctionne
        health = await DatabaseHealthCheck.check_connection()
        if health["status"] != "healthy":
            raise Exception(f"Database health check failed after reset: {health}")
        
        logger.info("✅ Reset de la base de données terminé avec succès")
        return True
        
    except Exception as e:
        logger.error("❌ Erreur reset base de données", error=str(e))
        return False
    
    finally:
        await close_database()


async def check_database():
    """
    Vérifier l'état de la base de données
    """
    
    try:
        logger.info("🔍 Vérification de la base de données...")
        
        # Health check
        health = await DatabaseHealthCheck.check_connection()
        logger.info("💊 Health check:", **health)
        
        # Performance check
        performance = await DatabaseHealthCheck.check_performance()
        logger.info("🚀 Performance:", **performance)
        
        if health["status"] == "healthy":
            logger.info("✅ Base de données en bonne santé")
            return True
        else:
            logger.error("❌ Base de données en mauvaise santé")
            return False
        
    except Exception as e:
        logger.error("❌ Erreur vérification base de données", error=str(e))
        return False
    
    finally:
        await close_database()


async def migrate_database():
    """
    Appliquer les migrations de base de données
    Pour l'instant, fait juste un setup (dans le futur, utiliser Alembic)
    """
    
    try:
        logger.info("🔄 Migration de la base de données...")
        
        # Pour l'instant, juste initialiser
        # Dans le futur: utiliser Alembic pour les vraies migrations
        await init_database()
        
        logger.info("✅ Migrations appliquées avec succès")
        return True
        
    except Exception as e:
        logger.error("❌ Erreur migration base de données", error=str(e))
        return False
    
    finally:
        await close_database()


async def seed_database():
    """
    Peupler la base de données avec des données de test/demo
    """
    
    try:
        logger.info("🌱 Peuplement de la base de données avec des données de démo...")
        
        from api.models import AsyncSessionLocal, Debate, AudioFile, Collection, ScheduledSession
        from api.models.debates import DebateType, DebateStatus
        from datetime import datetime, date
        import uuid
        
        async with AsyncSessionLocal() as db:
            # Créer quelques débats de démo
            demo_debates = [
                Debate(
                    id=str(uuid.uuid4()),
                    title="Séance publique du 9 juin 2025",
                    description="Discussion du projet de loi relatif à la transition énergétique",
                    type=DebateType.SEANCE_PUBLIQUE,
                    status=DebateStatus.DISPONIBLE,
                    date=date(2025, 6, 9),
                    start_time=datetime(2025, 6, 9, 15, 0),
                    end_time=datetime(2025, 6, 9, 18, 30),
                    duration_minutes=210,
                    source_url="https://videos.assemblee-nationale.fr/video.12345",
                    commission=None,
                    salle="Hémicycle",
                    speakers=["M. Dupont", "Mme Martin", "M. Legrand"],
                    ministers=["M. Le Ministre de l'Écologie"],
                    tags=["transition énergétique", "amendements", "écologie"],
                    view_count=1250
                ),
                Debate(
                    id=str(uuid.uuid4()),
                    title="Commission des finances - Audition du ministre de l'Économie",
                    description="Audition sur le projet de loi de finances 2026",
                    type=DebateType.COMMISSION,
                    status=DebateStatus.EN_COURS,
                    date=date(2025, 6, 9),
                    start_time=datetime(2025, 6, 9, 14, 0),
                    source_url="https://videos.assemblee-nationale.fr/video.12346",
                    commission="Finances",
                    salle="Salle 6350",
                    speakers=["M. Le Maire", "Mme Dubois"],
                    tags=["finances", "budget", "économie"],
                    view_count=845
                ),
                Debate(
                    id=str(uuid.uuid4()),
                    title="Questions au gouvernement",
                    description="Séance de questions orales au gouvernement",
                    type=DebateType.QUESTION_GOUVERNEMENT,
                    status=DebateStatus.TERMINE,
                    date=date(2025, 6, 8),
                    start_time=datetime(2025, 6, 8, 15, 0),
                    end_time=datetime(2025, 6, 8, 16, 0),
                    duration_minutes=60,
                    source_url="https://videos.assemblee-nationale.fr/video.12347",
                    salle="Hémicycle",
                    speakers=["Divers députés"],
                    ministers=["Premier ministre", "Plusieurs ministres"],
                    tags=["questions", "gouvernement", "actualité"],
                    view_count=2100
                )
            ]
            
            for debate in demo_debates:
                db.add(debate)
            
            await db.commit()
            
            # Créer des fichiers audio pour certains débats
            audio_files = [
                AudioFile(
                    id=str(uuid.uuid4()),
                    debate_id=demo_debates[0].id,
                    filename=f"debate_{demo_debates[0].id}_audio.mp3",
                    file_path=str(settings.paths.audio_dir / f"debate_{demo_debates[0].id}_audio.mp3"),
                    file_size=152428544,  # ~145 MB
                    format="mp3",
                    quality="192k",
                    duration_seconds=12600,  # 3h30
                    extraction_status="completed",
                    extraction_started_at=datetime.now(),
                    extraction_completed_at=datetime.now(),
                    stream_url=f"/api/streaming/{demo_debates[0].id}/stream",
                    download_url=f"/api/streaming/{demo_debates[0].id}/download"
                ),
                AudioFile(
                    id=str(uuid.uuid4()),
                    debate_id=demo_debates[2].id,
                    filename=f"debate_{demo_debates[2].id}_audio.mp3",
                    file_path=str(settings.paths.audio_dir / f"debate_{demo_debates[2].id}_audio.mp3"),
                    file_size=84234567,  # ~80 MB
                    format="mp3",
                    quality="192k",
                    duration_seconds=3600,  # 1h
                    extraction_status="completed",
                    extraction_started_at=datetime.now(),
                    extraction_completed_at=datetime.now(),
                    stream_url=f"/api/streaming/{demo_debates[2].id}/stream",
                    download_url=f"/api/streaming/{demo_debates[2].id}/download"
                )
            ]
            
            for audio_file in audio_files:
                db.add(audio_file)
            
            # Créer des sessions programmées
            scheduled_sessions = [
                ScheduledSession(
                    id=str(uuid.uuid4()),
                    date=date(2025, 6, 10),
                    start_time="09:00",
                    title="Séance publique - Suite du projet de loi transition énergétique",
                    type=DebateType.SEANCE_PUBLIQUE,
                    salle="Hémicycle",
                    url="https://videos.assemblee-nationale.fr/live"
                ),
                ScheduledSession(
                    id=str(uuid.uuid4()),
                    date=date(2025, 6, 10),
                    start_time="14:00",
                    title="Commission des finances - Examen des amendements",
                    type=DebateType.COMMISSION,
                    commission="Finances",
                    salle="Salle 6350"
                )
            ]
            
            for session in scheduled_sessions:
                db.add(session)
            
            # Créer quelques collections de démo
            demo_collections = [
                Collection(
                    id=str(uuid.uuid4()),
                    name="Transition énergétique",
                    description="Tous les débats sur la transition énergétique et l'écologie",
                    is_public=True,
                    color="#22c55e",
                    icon="leaf",
                    debate_count=1
                ),
                Collection(
                    id=str(uuid.uuid4()),
                    name="Questions au gouvernement",
                    description="Collection des séances de questions au gouvernement",
                    is_public=True,
                    color="#3b82f6",
                    icon="question-mark",
                    debate_count=1
                )
            ]
            
            for collection in demo_collections:
                db.add(collection)
            
            await db.commit()
            
            logger.info("✅ Données de démo créées avec succès")
            logger.info(f"   📺 {len(demo_debates)} débats")
            logger.info(f"   🎵 {len(audio_files)} fichiers audio")
            logger.info(f"   📅 {len(scheduled_sessions)} sessions programmées")
            logger.info(f"   📂 {len(demo_collections)} collections")
            
        return True
        
    except Exception as e:
        logger.error("❌ Erreur peuplement base de données", error=str(e))
        return False
    
    finally:
        await close_database()


def main():
    """
    Point d'entrée principal du script
    """
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestion de la base de données RobianAPI")
    parser.add_argument(
        "action", 
        choices=["setup", "reset", "check", "migrate", "seed"],
        help="Action à effectuer"
    )
    parser.add_argument(
        "--force", 
        action="store_true",
        help="Forcer l'action sans confirmation (dangereux!)"
    )
    
    args = parser.parse_args()
    
    # Configurer le logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger.info("🚀 Script de gestion base de données RobianAPI")
    logger.info(f"   Action: {args.action}")
    logger.info(f"   Environnement: {settings.app.environment}")
    logger.info(f"   Base de données: {settings.database.database_url}")
    
    # Exécuter l'action demandée
    success = False
    
    if args.action == "setup":
        success = asyncio.run(setup_database())
    elif args.action == "reset":
        if args.force or settings.app.environment != "production":
            success = asyncio.run(reset_database())
        else:
            logger.error("❌ Reset nécessite --force ou environment != production")
    elif args.action == "check":
        success = asyncio.run(check_database())
    elif args.action == "migrate":
        success = asyncio.run(migrate_database())
    elif args.action == "seed":
        success = asyncio.run(seed_database())
    
    if success:
        logger.info("✅ Opération terminée avec succès")
        sys.exit(0)
    else:
        logger.error("❌ Opération échouée")
        sys.exit(1)


if __name__ == "__main__":
    main()
