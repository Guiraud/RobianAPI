"""
Router pour le streaming et l'extraction audio
"""

import asyncio
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ..models import get_db_session, Debate, AudioFile
from ..schemas import ExtractionRequest, ExtractionResponse, StreamingInfoResponse
from ..services import (
    cache_service, 
    websocket_manager, 
    notify_extraction_started,
    notify_extraction_completed,
    notify_extraction_failed
)
from ..config import settings
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/streaming", tags=["streaming"])

# Stockage temporaire des tâches d'extraction
extraction_tasks: Dict[str, Dict[str, Any]] = {}


@router.get("/{debate_id}/info", response_model=StreamingInfoResponse)
async def get_streaming_info(
    debate_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtenir les informations de streaming pour un débat
    """
    
    cache_key = f"streaming_info_{debate_id}"
    
    # Cache check (TTL plus long pour les infos de streaming)
    cached_info = await cache_service.get("streaming", cache_key)
    if cached_info:
        return StreamingInfoResponse(**cached_info)
    
    try:
        # Récupérer le débat et ses fichiers audio
        query = select(Debate).options(joinedload(Debate.audio_files)).where(Debate.id == debate_id)
        result = await db.execute(query)
        debate = result.scalars().first()
        
        if not debate:
            raise HTTPException(status_code=404, detail=f"Débat {debate_id} non trouvé")
        
        # Chercher le fichier audio principal (completed)
        audio_file = None
        for af in debate.audio_files:
            if af.extraction_status == "completed":
                audio_file = af
                break
        
        if audio_file:
            # Audio disponible
            streaming_info = StreamingInfoResponse(
                debate_id=debate_id,
                audio_available=True,
                stream_url=f"/api/streaming/{debate_id}/stream",
                download_url=f"/api/streaming/{debate_id}/download",
                file_size=audio_file.file_size,
                duration_seconds=audio_file.duration_seconds,
                format=audio_file.format,
                quality=audio_file.quality,
                extraction_status=audio_file.extraction_status,
                message="Audio disponible pour streaming et téléchargement"
            )
        else:
            # Vérifier s'il y a une extraction en cours
            extracting_file = None
            for af in debate.audio_files:
                if af.extraction_status in ["pending", "extracting"]:
                    extracting_file = af
                    break
            
            if extracting_file:
                streaming_info = StreamingInfoResponse(
                    debate_id=debate_id,
                    audio_available=False,
                    extraction_status=extracting_file.extraction_status,
                    message=f"Extraction audio en cours ({extracting_file.extraction_status})"
                )
            else:
                streaming_info = StreamingInfoResponse(
                    debate_id=debate_id,
                    audio_available=False,
                    message="Aucun fichier audio disponible. Vous pouvez demander une extraction."
                )
        
        # Cache pour 1 heure (les infos de streaming changent peu)
        await cache_service.set("streaming", cache_key, streaming_info.model_dump(), ttl=3600)
        
        return streaming_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Erreur récupération infos streaming", debate_id=debate_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des informations de streaming")


@router.post("/{debate_id}/extract", response_model=ExtractionResponse)
async def request_extraction(
    debate_id: str,
    extraction_request: ExtractionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Demander l'extraction audio d'un débat
    """
    
    try:
        # Vérifier que le débat existe
        query = select(Debate).options(joinedload(Debate.audio_files)).where(Debate.id == debate_id)
        result = await db.execute(query)
        debate = result.scalars().first()
        
        if not debate:
            raise HTTPException(status_code=404, detail=f"Débat {debate_id} non trouvé")
        
        # Vérifier s'il y a déjà un fichier audio prêt
        for audio_file in debate.audio_files:
            if audio_file.extraction_status == "completed":
                return ExtractionResponse(
                    extraction_id=audio_file.id,
                    debate_id=debate_id,
                    status="completed",
                    message="Audio déjà disponible",
                    audio_file=audio_file.to_dict()
                )
        
        # Vérifier s'il y a déjà une extraction en cours
        for audio_file in debate.audio_files:
            if audio_file.extraction_status in ["pending", "extracting"]:
                return ExtractionResponse(
                    extraction_id=audio_file.id,
                    debate_id=debate_id,
                    status=audio_file.extraction_status,
                    message=f"Extraction déjà en cours ({audio_file.extraction_status})",
                    estimated_duration="5-10 minutes"
                )
        
        # Créer un nouveau fichier audio pour l'extraction
        extraction_id = str(uuid.uuid4())
        filename = f"debate_{debate_id}_{int(datetime.now().timestamp())}.{extraction_request.format}"
        file_path = settings.paths.audio_dir / filename
        
        audio_file = AudioFile(
            id=extraction_id,
            debate_id=debate_id,
            filename=filename,
            file_path=str(file_path),
            file_size=0,  # Sera mis à jour après extraction
            format=extraction_request.format,
            quality=extraction_request.quality,
            extraction_status="pending",
            extraction_started_at=datetime.now()
        )
        
        db.add(audio_file)
        await db.commit()
        await db.refresh(audio_file)
        
        # Démarrer l'extraction en arrière-plan
        background_tasks.add_task(
            perform_audio_extraction,
            extraction_id=extraction_id,
            debate=debate,
            audio_file=audio_file,
            extraction_request=extraction_request
        )
        
        # Invalider le cache
        await cache_service.delete("streaming", f"streaming_info_{debate_id}")
        
        # Notifier via WebSocket
        await notify_extraction_started(debate_id, extraction_id)
        
        logger.info("🎵 Extraction audio démarrée", 
                   debate_id=debate_id, 
                   extraction_id=extraction_id,
                   priority=extraction_request.priority)
        
        return ExtractionResponse(
            extraction_id=extraction_id,
            debate_id=debate_id,
            status="pending",
            message="Extraction audio démarrée",
            estimated_duration="5-10 minutes"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("❌ Erreur demande extraction", debate_id=debate_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la demande d'extraction")


@router.get("/{debate_id}/stream")
async def stream_audio(
    debate_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Streamer le fichier audio d'un débat
    """
    
    try:
        # Récupérer le fichier audio prêt
        query = (
            select(AudioFile)
            .where(AudioFile.debate_id == debate_id)
            .where(AudioFile.extraction_status == "completed")
            .order_by(AudioFile.created_at.desc())
        )
        result = await db.execute(query)
        audio_file = result.scalars().first()
        
        if not audio_file:
            raise HTTPException(status_code=404, detail="Aucun fichier audio disponible pour ce débat")
        
        file_path = Path(audio_file.file_path)
        if not file_path.exists():
            logger.error("❌ Fichier audio manquant", 
                        debate_id=debate_id, 
                        file_path=str(file_path))
            raise HTTPException(status_code=404, detail="Fichier audio introuvable sur le serveur")
        
        # Incrémenter le compteur de stream
        audio_file.stream_count += 1
        await db.commit()
        
        # Headers pour le streaming
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Length": str(audio_file.file_size),
            "Content-Type": f"audio/{audio_file.format}",
            "Content-Disposition": f'inline; filename="{audio_file.filename}"'
        }
        
        logger.info("🎵 Streaming audio", 
                   debate_id=debate_id, 
                   file_size=audio_file.file_size_mb)
        
        return FileResponse(
            path=file_path,
            headers=headers,
            media_type=f"audio/{audio_file.format}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Erreur streaming audio", debate_id=debate_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors du streaming audio")


@router.get("/{debate_id}/download")
async def download_audio(
    debate_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Télécharger le fichier audio d'un débat
    """
    
    try:
        # Récupérer le fichier audio prêt
        query = (
            select(AudioFile)
            .where(AudioFile.debate_id == debate_id)
            .where(AudioFile.extraction_status == "completed")
            .order_by(AudioFile.created_at.desc())
        )
        result = await db.execute(query)
        audio_file = result.scalars().first()
        
        if not audio_file:
            raise HTTPException(status_code=404, detail="Aucun fichier audio disponible pour ce débat")
        
        file_path = Path(audio_file.file_path)
        if not file_path.exists():
            logger.error("❌ Fichier audio manquant", 
                        debate_id=debate_id, 
                        file_path=str(file_path))
            raise HTTPException(status_code=404, detail="Fichier audio introuvable sur le serveur")
        
        # Incrémenter le compteur de téléchargement
        audio_file.download_count += 1
        
        # Incrémenter aussi le compteur global du débat
        debate_query = select(Debate).where(Debate.id == debate_id)
        debate_result = await db.execute(debate_query)
        debate = debate_result.scalars().first()
        if debate:
            debate.download_count += 1
        
        await db.commit()
        
        # Headers pour le téléchargement
        headers = {
            "Content-Disposition": f'attachment; filename="{audio_file.filename}"',
            "Content-Length": str(audio_file.file_size),
        }
        
        logger.info("📥 Téléchargement audio", 
                   debate_id=debate_id, 
                   file_size=audio_file.file_size_mb)
        
        return FileResponse(
            path=file_path,
            headers=headers,
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Erreur téléchargement audio", debate_id=debate_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors du téléchargement audio")


@router.get("/{debate_id}/status", response_model=ExtractionResponse)
async def get_extraction_status(
    debate_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Obtenir le statut de l'extraction audio
    """
    
    try:
        # Récupérer le fichier audio le plus récent
        query = (
            select(AudioFile)
            .where(AudioFile.debate_id == debate_id)
            .order_by(AudioFile.created_at.desc())
        )
        result = await db.execute(query)
        audio_file = result.scalars().first()
        
        if not audio_file:
            raise HTTPException(status_code=404, detail="Aucune extraction trouvée pour ce débat")
        
        # Calculer la progression si en cours
        progress = None
        if audio_file.extraction_status == "extracting":
            # Estimation basée sur le temps écoulé
            if audio_file.extraction_started_at:
                elapsed = (datetime.now() - audio_file.extraction_started_at).total_seconds()
                estimated_total = 600  # 10 minutes estimation
                progress = min(90, int((elapsed / estimated_total) * 100))
        
        response = ExtractionResponse(
            extraction_id=audio_file.id,
            debate_id=debate_id,
            status=audio_file.extraction_status,
            message=_get_status_message(audio_file.extraction_status),
            progress=progress,
            error=audio_file.extraction_error,
            audio_file=audio_file.to_dict() if audio_file.extraction_status == "completed" else None
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Erreur statut extraction", debate_id=debate_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du statut")


async def perform_audio_extraction(
    extraction_id: str,
    debate: Debate,
    audio_file: AudioFile,
    extraction_request: ExtractionRequest
):
    """
    Effectuer l'extraction audio en arrière-plan
    Cette fonction simule l'extraction - en production, utiliser yt-dlp + FFmpeg
    """
    
    try:
        # Mettre à jour le statut à "extracting"
        from ..models import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            # Récupérer le fichier audio
            query = select(AudioFile).where(AudioFile.id == extraction_id)
            result = await db.execute(query)
            current_audio_file = result.scalars().first()
            
            if not current_audio_file:
                logger.error("❌ AudioFile non trouvé", extraction_id=extraction_id)
                return
            
            current_audio_file.extraction_status = "extracting"
            await db.commit()
        
        # Invalider le cache
        await cache_service.delete("streaming", f"streaming_info_{debate.id}")
        
        logger.info("🎵 Début extraction audio", 
                   debate_id=debate.id, 
                   extraction_id=extraction_id,
                   source_url=debate.source_url)
        
        # SIMULATION - En production, remplacer par vraie extraction
        if settings.app.environment == "development":
            # Simulation d'extraction (3-8 secondes)
            import random
            await asyncio.sleep(random.uniform(3, 8))
            
            # Simuler un fichier audio créé
            file_path = Path(audio_file.file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Créer un fichier vide pour la démo
            file_path.write_text("# Fichier audio simulé pour démo\n")
            file_size = 150 * 1024 * 1024  # 150 MB simulés
            duration_seconds = 7800  # 2h10 simulées
        else:
            # EN PRODUCTION: Ici utiliser yt-dlp + FFmpeg
            # from scripts.extract_audio import extract_audio_from_url
            # file_path, file_size, duration_seconds = await extract_audio_from_url(
            #     debate.source_url,
            #     audio_file.file_path,
            #     format=extraction_request.format,
            #     quality=extraction_request.quality
            # )
            raise NotImplementedError("Production extraction not implemented yet")
        
        # Mettre à jour le fichier audio avec les résultats
        async with AsyncSessionLocal() as db:
            query = select(AudioFile).where(AudioFile.id == extraction_id)
            result = await db.execute(query)
            final_audio_file = result.scalars().first()
            
            if final_audio_file:
                final_audio_file.extraction_status = "completed"
                final_audio_file.extraction_completed_at = datetime.now()
                final_audio_file.file_size = file_size
                final_audio_file.duration_seconds = duration_seconds
                final_audio_file.stream_url = f"/api/streaming/{debate.id}/stream"
                final_audio_file.download_url = f"/api/streaming/{debate.id}/download"
                
                await db.commit()
        
        # Invalider le cache
        await cache_service.delete("streaming", f"streaming_info_{debate.id}")
        await cache_service.delete("debates", f"detail_{debate.id}")
        
        # Notifier via WebSocket
        await notify_extraction_completed(
            debate.id, 
            extraction_id, 
            f"/api/streaming/{debate.id}/stream",
            file_size
        )
        
        logger.info("✅ Extraction audio terminée", 
                   debate_id=debate.id, 
                   extraction_id=extraction_id,
                   file_size_mb=round(file_size / (1024*1024), 2),
                   duration_seconds=duration_seconds)
        
    except Exception as e:
        # Marquer l'extraction comme échouée
        try:
            async with AsyncSessionLocal() as db:
                query = select(AudioFile).where(AudioFile.id == extraction_id)
                result = await db.execute(query)
                failed_audio_file = result.scalars().first()
                
                if failed_audio_file:
                    failed_audio_file.extraction_status = "error"
                    failed_audio_file.extraction_error = str(e)
                    await db.commit()
            
            # Notifier l'échec
            await notify_extraction_failed(debate.id, extraction_id, str(e))
            
        except Exception as update_error:
            logger.error("❌ Erreur mise à jour statut échec", error=str(update_error))
        
        logger.error("❌ Échec extraction audio", 
                    debate_id=debate.id, 
                    extraction_id=extraction_id, 
                    error=str(e))


def _get_status_message(status: str) -> str:
    """Obtenir un message user-friendly pour le statut"""
    messages = {
        "pending": "Extraction en attente de démarrage",
        "extracting": "Extraction audio en cours...",
        "completed": "Extraction terminée avec succès",
        "error": "Erreur lors de l'extraction"
    }
    return messages.get(status, f"Statut inconnu: {status}")


# Routes de compatibilité avec l'ancienne API
@router.get("/legacy/{debate_id}/stream", include_in_schema=False)
async def legacy_stream(debate_id: str, db: AsyncSession = Depends(get_db_session)):
    """Route de compatibilité pour l'ancien endpoint de streaming"""
    return await stream_audio(debate_id, db)


@router.get("/legacy/{debate_id}/file", include_in_schema=False)
async def legacy_download(debate_id: str, db: AsyncSession = Depends(get_db_session)):
    """Route de compatibilité pour l'ancien endpoint de téléchargement"""
    return await download_audio(debate_id, db)
