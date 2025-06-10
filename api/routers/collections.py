"""
Router pour les collections et favoris utilisateur
"""

import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, delete
from sqlalchemy.orm import joinedload

from ..models import get_db_session, Collection, Favorite, Debate, UserActivity, ActivityType, collection_debates
from ..services import cache_service
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.get("/", response_model=List[dict])
async def list_collections(
    user_id: Optional[str] = None,
    include_public: bool = True,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Lister les collections d'un utilisateur
    """
    
    cache_key = f"collections_{user_id}_{include_public}"
    cached_collections = await cache_service.get("metadata", cache_key)
    if cached_collections:
        return cached_collections
    
    try:
        # Construction de la requête
        query = select(Collection)
        
        filters = []
        if user_id:
            filters.append(Collection.user_id == user_id)
        if include_public:
            filters.append(Collection.is_public == True)
        
        if filters:
            if user_id and include_public:
                # Collections de l'utilisateur OU publiques
                query = query.where(
                    (Collection.user_id == user_id) | (Collection.is_public == True)
                )
            else:
                query = query.where(and_(*filters))
        
        # Tri par ordre puis par nom
        query = query.order_by(Collection.sort_order, Collection.name)
        
        result = await db.execute(query)
        collections = result.scalars().all()
        
        # Convertir en dictionnaire
        collections_data = [collection.to_dict() for collection in collections]
        
        # Cache pour 30 minutes
        await cache_service.set("metadata", cache_key, collections_data, ttl=1800)
        
        logger.info("📂 Collections récupérées", 
                   count=len(collections), user_id=user_id)
        
        return collections_data
        
    except Exception as e:
        logger.error("❌ Erreur récupération collections", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des collections")


@router.post("/", response_model=dict)
async def create_collection(
    name: str,
    description: Optional[str] = None,
    user_id: Optional[str] = None,
    is_public: bool = False,
    color: Optional[str] = None,
    icon: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Créer une nouvelle collection
    """
    
    try:
        # Vérifier si une collection avec ce nom existe déjà pour cet utilisateur
        existing_query = select(Collection).where(
            Collection.name == name,
            Collection.user_id == user_id
        )
        existing_result = await db.execute(existing_query)
        existing_collection = existing_result.scalars().first()
        
        if existing_collection:
            raise HTTPException(status_code=409, detail="Une collection avec ce nom existe déjà")
        
        # Créer la nouvelle collection
        collection = Collection(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            user_id=user_id,
            is_public=is_public,
            color=color,
            icon=icon,
            sort_order=0  # Sera mis à jour si nécessaire
        )
        
        db.add(collection)
        await db.commit()
        await db.refresh(collection)
        
        # Invalider le cache
        await cache_service.clear_namespace("metadata")
        
        # Enregistrer l'activité
        if user_id:
            activity = UserActivity(
                id=str(uuid.uuid4()),
                user_id=user_id,
                action_type=ActivityType.CREATE_COLLECTION,
                collection_id=collection.id,
                action_data={"collection_name": name}
            )
            db.add(activity)
            await db.commit()
        
        logger.info("✅ Collection créée", 
                   collection_id=collection.id, 
                   name=name, 
                   user_id=user_id)
        
        return collection.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("❌ Erreur création collection", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la création de la collection")


@router.get("/{collection_id}", response_model=dict)
async def get_collection(
    collection_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Récupérer une collection spécifique avec ses débats
    """
    
    cache_key = f"collection_detail_{collection_id}"
    cached_collection = await cache_service.get("metadata", cache_key)
    if cached_collection:
        return cached_collection
    
    try:
        # Récupérer la collection
        collection_query = select(Collection).where(Collection.id == collection_id)
        collection_result = await db.execute(collection_query)
        collection = collection_result.scalars().first()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection non trouvée")
        
        # Récupérer les débats de la collection
        debates_query = (
            select(Debate)
            .join(collection_debates)
            .where(collection_debates.c.collection_id == collection_id)
            .order_by(Debate.date.desc())
        )
        debates_result = await db.execute(debates_query)
        debates = debates_result.scalars().all()
        
        # Construire la réponse
        collection_data = collection.to_dict()
        collection_data["debates"] = [debate.to_dict() for debate in debates]
        collection_data["actual_debate_count"] = len(debates)
        
        # Cache pour 1 heure
        await cache_service.set("metadata", cache_key, collection_data, ttl=3600)
        
        return collection_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Erreur récupération collection", collection_id=collection_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de la collection")


@router.put("/{collection_id}", response_model=dict)
async def update_collection(
    collection_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_public: Optional[bool] = None,
    color: Optional[str] = None,
    icon: Optional[str] = None,
    sort_order: Optional[int] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Mettre à jour une collection
    """
    
    try:
        # Récupérer la collection
        query = select(Collection).where(Collection.id == collection_id)
        result = await db.execute(query)
        collection = result.scalars().first()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection non trouvée")
        
        # Mettre à jour les champs fournis
        if name is not None:
            collection.name = name
        if description is not None:
            collection.description = description
        if is_public is not None:
            collection.is_public = is_public
        if color is not None:
            collection.color = color
        if icon is not None:
            collection.icon = icon
        if sort_order is not None:
            collection.sort_order = sort_order
        
        await db.commit()
        await db.refresh(collection)
        
        # Invalider le cache
        await cache_service.delete("metadata", f"collection_detail_{collection_id}")
        await cache_service.clear_namespace("metadata")
        
        logger.info("📝 Collection mise à jour", collection_id=collection_id)
        
        return collection.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("❌ Erreur mise à jour collection", collection_id=collection_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour de la collection")


@router.delete("/{collection_id}")
async def delete_collection(
    collection_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Supprimer une collection
    """
    
    try:
        # Récupérer la collection
        query = select(Collection).where(Collection.id == collection_id)
        result = await db.execute(query)
        collection = result.scalars().first()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection non trouvée")
        
        # Supprimer (les associations seront supprimées automatiquement)
        await db.delete(collection)
        await db.commit()
        
        # Invalider le cache
        await cache_service.delete("metadata", f"collection_detail_{collection_id}")
        await cache_service.clear_namespace("metadata")
        
        logger.info("🗑️ Collection supprimée", collection_id=collection_id)
        
        return {"message": f"Collection {collection_id} supprimée avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("❌ Erreur suppression collection", collection_id=collection_id, error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression de la collection")


@router.post("/{collection_id}/debates/{debate_id}")
async def add_debate_to_collection(
    collection_id: str,
    debate_id: str,
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Ajouter un débat à une collection
    """
    
    try:
        # Vérifier que la collection existe
        collection_query = select(Collection).where(Collection.id == collection_id)
        collection_result = await db.execute(collection_query)
        collection = collection_result.scalars().first()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection non trouvée")
        
        # Vérifier que le débat existe
        debate_query = select(Debate).where(Debate.id == debate_id)
        debate_result = await db.execute(debate_query)
        debate = debate_result.scalars().first()
        
        if not debate:
            raise HTTPException(status_code=404, detail="Débat non trouvé")
        
        # Vérifier si l'association existe déjà
        existing_query = select(collection_debates).where(
            collection_debates.c.collection_id == collection_id,
            collection_debates.c.debate_id == debate_id
        )
        existing_result = await db.execute(existing_query)
        existing = existing_result.first()
        
        if existing:
            raise HTTPException(status_code=409, detail="Ce débat est déjà dans la collection")
        
        # Ajouter l'association
        insert_stmt = collection_debates.insert().values(
            collection_id=collection_id,
            debate_id=debate_id
        )
        await db.execute(insert_stmt)
        
        # Mettre à jour le compteur de débats
        collection.debate_count += 1
        
        await db.commit()
        
        # Invalider le cache
        await cache_service.delete("metadata", f"collection_detail_{collection_id}")
        await cache_service.clear_namespace("metadata")
        
        # Enregistrer l'activité
        if user_id:
            activity = UserActivity(
                id=str(uuid.uuid4()),
                user_id=user_id,
                action_type=ActivityType.ADD_TO_COLLECTION,
                debate_id=debate_id,
                collection_id=collection_id,
                action_data={
                    "collection_name": collection.name,
                    "debate_title": debate.title
                }
            )
            db.add(activity)
            await db.commit()
        
        logger.info("➕ Débat ajouté à collection", 
                   collection_id=collection_id, 
                   debate_id=debate_id)
        
        return {"message": f"Débat ajouté à la collection '{collection.name}'"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("❌ Erreur ajout débat à collection", 
                    collection_id=collection_id, 
                    debate_id=debate_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de l'ajout du débat à la collection")


@router.delete("/{collection_id}/debates/{debate_id}")
async def remove_debate_from_collection(
    collection_id: str,
    debate_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retirer un débat d'une collection
    """
    
    try:
        # Vérifier que l'association existe
        existing_query = select(collection_debates).where(
            collection_debates.c.collection_id == collection_id,
            collection_debates.c.debate_id == debate_id
        )
        existing_result = await db.execute(existing_query)
        existing = existing_result.first()
        
        if not existing:
            raise HTTPException(status_code=404, detail="Ce débat n'est pas dans la collection")
        
        # Supprimer l'association
        delete_stmt = delete(collection_debates).where(
            collection_debates.c.collection_id == collection_id,
            collection_debates.c.debate_id == debate_id
        )
        await db.execute(delete_stmt)
        
        # Mettre à jour le compteur de débats
        collection_query = select(Collection).where(Collection.id == collection_id)
        collection_result = await db.execute(collection_query)
        collection = collection_result.scalars().first()
        
        if collection and collection.debate_count > 0:
            collection.debate_count -= 1
        
        await db.commit()
        
        # Invalider le cache
        await cache_service.delete("metadata", f"collection_detail_{collection_id}")
        await cache_service.clear_namespace("metadata")
        
        logger.info("➖ Débat retiré de collection", 
                   collection_id=collection_id, 
                   debate_id=debate_id)
        
        return {"message": "Débat retiré de la collection"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("❌ Erreur suppression débat de collection", 
                    collection_id=collection_id, 
                    debate_id=debate_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression du débat de la collection")


# =============================================================================
# FAVORIS
# =============================================================================

favorites_router = APIRouter(prefix="/api/favorites", tags=["favorites"])


@favorites_router.get("/", response_model=List[dict])
async def list_favorites(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Lister les favoris d'un utilisateur
    """
    
    cache_key = f"favorites_{user_id}"
    cached_favorites = await cache_service.get("metadata", cache_key)
    if cached_favorites:
        return cached_favorites
    
    try:
        # Récupérer les favoris avec les débats associés
        query = (
            select(Favorite)
            .options(joinedload(Favorite.debate))
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc())
        )
        
        result = await db.execute(query)
        favorites = result.scalars().unique().all()
        
        # Convertir en dictionnaire avec les détails du débat
        favorites_data = []
        for favorite in favorites:
            favorite_dict = favorite.to_dict()
            if favorite.debate:
                favorite_dict["debate"] = favorite.debate.to_dict()
            favorites_data.append(favorite_dict)
        
        # Cache pour 10 minutes
        await cache_service.set("metadata", cache_key, favorites_data, ttl=600)
        
        logger.info("⭐ Favoris récupérés", 
                   count=len(favorites), user_id=user_id)
        
        return favorites_data
        
    except Exception as e:
        logger.error("❌ Erreur récupération favoris", error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des favoris")


@favorites_router.post("/{debate_id}")
async def add_favorite(
    debate_id: str,
    user_id: Optional[str] = None,
    note: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Ajouter un débat aux favoris
    """
    
    try:
        # Vérifier que le débat existe
        debate_query = select(Debate).where(Debate.id == debate_id)
        debate_result = await db.execute(debate_query)
        debate = debate_result.scalars().first()
        
        if not debate:
            raise HTTPException(status_code=404, detail="Débat non trouvé")
        
        # Vérifier si déjà en favori
        existing_query = select(Favorite).where(
            Favorite.debate_id == debate_id,
            Favorite.user_id == user_id
        )
        existing_result = await db.execute(existing_query)
        existing_favorite = existing_result.scalars().first()
        
        if existing_favorite:
            raise HTTPException(status_code=409, detail="Ce débat est déjà dans vos favoris")
        
        # Créer le favori
        favorite = Favorite(
            id=str(uuid.uuid4()),
            user_id=user_id,
            debate_id=debate_id,
            note=note
        )
        
        db.add(favorite)
        await db.commit()
        await db.refresh(favorite)
        
        # Invalider le cache
        await cache_service.delete("metadata", f"favorites_{user_id}")
        
        # Enregistrer l'activité
        if user_id:
            activity = UserActivity(
                id=str(uuid.uuid4()),
                user_id=user_id,
                action_type=ActivityType.ADD_FAVORITE,
                debate_id=debate_id,
                action_data={"debate_title": debate.title}
            )
            db.add(activity)
            await db.commit()
        
        logger.info("⭐ Favori ajouté", 
                   debate_id=debate_id, 
                   user_id=user_id)
        
        return {"message": f"Débat '{debate.title}' ajouté aux favoris"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("❌ Erreur ajout favori", 
                    debate_id=debate_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de l'ajout aux favoris")


@favorites_router.delete("/{debate_id}")
async def remove_favorite(
    debate_id: str,
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retirer un débat des favoris
    """
    
    try:
        # Récupérer le favori
        query = select(Favorite).where(
            Favorite.debate_id == debate_id,
            Favorite.user_id == user_id
        )
        result = await db.execute(query)
        favorite = result.scalars().first()
        
        if not favorite:
            raise HTTPException(status_code=404, detail="Ce débat n'est pas dans vos favoris")
        
        # Supprimer le favori
        await db.delete(favorite)
        await db.commit()
        
        # Invalider le cache
        await cache_service.delete("metadata", f"favorites_{user_id}")
        
        # Enregistrer l'activité
        if user_id:
            activity = UserActivity(
                id=str(uuid.uuid4()),
                user_id=user_id,
                action_type=ActivityType.REMOVE_FAVORITE,
                debate_id=debate_id,
                action_data={"action": "removed"}
            )
            db.add(activity)
            await db.commit()
        
        logger.info("⭐ Favori supprimé", 
                   debate_id=debate_id, 
                   user_id=user_id)
        
        return {"message": "Débat retiré des favoris"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("❌ Erreur suppression favori", 
                    debate_id=debate_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Erreur lors de la suppression du favori")


# Ajouter le router des favoris au router principal des collections
router.include_router(favorites_router)
