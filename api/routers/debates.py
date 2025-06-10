"""
Router pour les débats de l'Assemblée nationale
"""

import asyncio
from typing import List, Optional
from datetime import datetime, date

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import joinedload

from ..models import get_db_session, Debate, AudioFile, DebateType, DebateStatus
from ..schemas import (
    DebateResponse, 
    DebateListResponse, 
    DebateSearchFilters,
    DebateCreate,
    DebateUpdate
)
from ..services import (
    cache_service, 
    websocket_manager, 
    WebSocketMessage, 
    MessageType
)
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/debates", tags=["debates"])


@router.get("/", response_model=DebateListResponse)
async def list_debates(
    q: Optional[str] = Query(None, description="Recherche textuelle"),
    type: Optional[DebateType] = Query(None, description="Type de débat"),
    status: Optional[DebateStatus] = Query(None, description="Statut du débat"),
    commission: Optional[str] = Query(None, description="Commission"),
    date_start: Optional[date] = Query(None, description="Date de début"),
    date_end: Optional[date] = Query(None, description="Date de fin"),
    has_audio: Optional[bool] = Query(None, description="Avec audio disponible"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    per_page: int = Query(20, ge=1, le=100, description="Éléments par page"),
    sort_by: str = Query("date", description="Champ de tri"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Ordre de tri"),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Liste des débats avec recherche et filtres avancés
    Utilise le cache Redis pour les performances
    """
    
    # Clé de cache basée sur tous les paramètres
    cache_key = f"list_{q}_{type}_{status}_{commission}_{date_start}_{date_end}_{has_audio}_{page}_{per_page}_{sort_by}_{sort_order}"
    
    # Tentative de récupération depuis le cache
    cached_result = await cache_service.get("debates", cache_key)
    if cached_result:
        logger.debug("📦 Débats depuis cache Redis", page=page, per_page=per_page)
        return cached_result
    
    try:
        # Construction de la requête de base
        query = select(Debate).options(joinedload(Debate.audio_files))
        count_query = select(func.count(Debate.id))
        
        # Filtres
        filters = []
        
        if q:
            # Recherche textuelle dans titre et description
            search_filter = or_(
                Debate.title.ilike(f"%{q}%"),
                Debate.description.ilike(f"%{q}%"),
                Debate.speakers.any(q),  # Recherche dans le tableau speakers
                Debate.tags.any(q)       # Recherche dans le tableau tags
            )
            filters.append(search_filter)
        
        if type:
            filters.append(Debate.type == type)
        
        if status:
            filters.append(Debate.status == status)
        
        if commission:
            filters.append(Debate.commission.ilike(f"%{commission}%"))
        
        if date_start:
            filters.append(Debate.date >= date_start)
        
        if date_end:
            filters.append(Debate.date <= date_end)
        
        if has_audio is not None:
            if has_audio:
                # Débats avec au moins un fichier audio prêt
                filters.append(
                    Debate.audio_files.any(AudioFile.extraction_status == "completed")
                )
            else:
                # Débats sans fichier audio ou en cours d'extraction
                filters.append(
                    or_(
                        ~Debate.audio_files.any(),
                        ~Debate.audio_files.any(AudioFile.extraction_status == "completed")
                    )
                )
        
        # Appliquer tous les filtres
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Tri
        sort_column = getattr(Debate, sort_by, Debate.date)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Exécution des requêtes
        result = await db.execute(query)
        debates = result.scalars().unique().all()
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Conversion en schémas de réponse
        debate_responses = [DebateResponse.model_validate(debate) for debate in debates]
        
        # Calcul de la pagination
        has_next = (page * per_page) < total
        has_prev = page > 1
        
        response = DebateListResponse(
            debates=debate_responses,
            total=total,
            page=page,
            per_page=per_page,
            has_next=has_next,
            has_prev=has_prev
        )
        
        # Mise en cache pour 5 minutes
        await cache_service.set("debates", cache_key, response.model_dump(), ttl=300)
        
        logger.info("📺 Débats récupérés depuis base de données", 
                   count=len(debates), page=page, total=total)
        
        return response
        
    except Exception as e:
        logger.error("❌ Erreur récupération débats", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des débats")


@router.get("/{debate_id}", response_model=DebateResponse)
async def get_debate(
    debate_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Récupérer les détails d'un débat spécifique
    Incrémente le compteur de vues de manière asynchrone
    """
    
    # Cache check
    cache_key = f"detail_{debate_id}"
    cached_debate = await cache_service.get("debates", cache_key)
    if cached_debate:
        # Incrémenter le compteur de vues en arrière-plan
        background_tasks.add_task(increment_view_count, debate_id, db)
        return DebateResponse(**cached_debate)
    
    try:
        # Requête avec jointure pour récupérer les fichiers audio
        query = select(Debate).options(joinedload(Debate.audio_files)).where(Debate.id == debate_id)
        result = await db.execute(query)
        debate = result.scalars().first()
        
        if not debate:
            raise HTTPException(status_code=404, detail=f"Débat {debate_id} non trouvé")
        
        # Conversion en schéma de réponse
        debate_response = DebateResponse.model_validate(debate)
        
        # Cache pour 1 heure
        await cache_service.set("debates", cache_key, debate_response.model_dump(), ttl=3600)
        
        # Incrémenter le compteur de vues en arrière-plan
        background_tasks.add_task(increment_view_count, debate_id, db)
        
        # Notifier via WebSocket
        await websocket_manager.broadcast_to_channel(
            f"debate:{debate_id}",
            WebSocketMessage(
                type=MessageType.SYSTEM_STATUS,
                channel=f"debate:{debate_id}",
                data={"action": "viewed", "debate_id": debate_id}
            )
        )
        
        logger.info("📺 Détail débat récupéré", debate_id=debate_id)
        return debate_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Erreur récupération débat", debate_id=debate_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du débat")


@router.post("/", response_model=DebateResponse)
async def create_debate(
    debate_data: DebateCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Créer un nouveau débat
    (Généralement utilisé par les scripts de scraping)
    """
    
    try:
        # Vérifier si un débat avec la même URL source existe déjà
        existing_query = select(Debate).where(Debate.source_url == debate_data.source_url)
        existing_result = await db.execute(existing_query)
        existing_debate = existing_result.scalars().first()
        
        if existing_debate:
            raise HTTPException(status_code=409, detail="Un débat avec cette URL source existe déjà")
        
        # Créer le nouveau débat
        debate = Debate(**debate_data.model_dump())
        db.add(debate)
        await db.commit()
        await db.refresh(debate)
        
        # Invalider le cache des listes
        await cache_service.clear_namespace("debates")
        
        # Notifier via WebSocket
        await websocket_manager.broadcast_to_channel(
            "debates",
            WebSocketMessage(
                type=MessageType.DEBATE_STARTED if debate.status == DebateStatus.EN_COURS else MessageType.SYSTEM_STATUS,
                channel="debates",
                data={"action": "created", "debate": debate.to_dict()}
            )
        )
        
        logger.info("✅ Nouveau débat créé", debate_id=debate.id, title=debate.title)
        
        return DebateResponse.model_validate(debate)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("❌ Erreur création débat", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la création du débat")


@router.put("/{debate_id}", response_model=DebateResponse)
async def update_debate(
    debate_id: str,
    debate_data: DebateUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Mettre à jour un débat existant
    """
    
    try:
        # Récupérer le débat existant
        query = select(Debate).where(Debate.id == debate_id)
        result = await db.execute(query)
        debate = result.scalars().first()
        
        if not debate:
            raise HTTPException(status_code=404, detail=f"Débat {debate_id} non trouvé")
        
        # Mettre à jour les champs fournis
        update_data = debate_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(debate, field, value)
        
        await db.commit()
        await db.refresh(debate)
        
        # Invalider le cache
        await cache_service.delete("debates", f"detail_{debate_id}")
        await cache_service.clear_namespace("debates")
        
        logger.info("📝 Débat mis à jour", debate_id=debate_id)
        
        return DebateResponse.model_validate(debate)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("❌ Erreur mise à jour débat", debate_id=debate_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour du débat")


@router.delete("/{debate_id}")
async def delete_debate(
    debate_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Supprimer un débat
    (Utilisation administrative uniquement)
    """
    
    try:
        # Récupérer le débat
        query = select(Debate).where(Debate.id == debate_id)
        result = await db.execute(query)
        debate = result.scalars().first()
        
        if not debate:
            raise HTTPException(status_code=404, detail=f"Débat {debate_id} non trouvé")
        
        # Supprimer (cascade supprimera aussi les audio_files)
        await db.delete(debate)
        await db.commit()
        
        # Invalider le cache
        await cache_service.delete("debates", f"detail_{debate_id}")
        await cache_service.clear_namespace("debates")
        
        logger.info("🗑️ Débat supprimé", debate_id=debate_id)
        
        return {"message": f"Débat {debate_id} supprimé avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("❌ Erreur suppression débat", debate_id=debate_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression du débat")


async def increment_view_count(debate_id: str, db: AsyncSession):
    """
    Incrémenter le compteur de vues de manière asynchrone
    """
    try:
        query = select(Debate).where(Debate.id == debate_id)
        result = await db.execute(query)
        debate = result.scalars().first()
        
        if debate:
            debate.view_count += 1
            await db.commit()
            
            # Invalider le cache pour forcer la mise à jour
            await cache_service.delete("debates", f"detail_{debate_id}")
            
            logger.debug("👀 Vue incrémentée", debate_id=debate_id, new_count=debate.view_count)
        
    except Exception as e:
        await db.rollback()
        logger.error("❌ Erreur incrémentation vue", debate_id=debate_id, error=str(e))


# Routes de compatibilité avec l'ancienne API
@router.get("/legacy/debats", include_in_schema=False)
async def legacy_list_debates(
    date_debut: Optional[str] = None,
    date_fin: Optional[str] = None,
    type_debat: Optional[str] = None,
    commission: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Route de compatibilité pour l'ancienne API
    Redirige vers la nouvelle API moderne
    """
    
    # Convertir les paramètres de l'ancienne API vers la nouvelle
    filters = {}
    if type_debat:
        filters["type"] = type_debat
    if commission:
        filters["commission"] = commission
    if date_debut:
        try:
            filters["date_start"] = datetime.fromisoformat(date_debut).date()
        except ValueError:
            pass
    if date_fin:
        try:
            filters["date_end"] = datetime.fromisoformat(date_fin).date()
        except ValueError:
            pass
    
    # Appeler la nouvelle API
    return await list_debates(
        per_page=min(limit, 100),
        db=db,
        **filters
    )
