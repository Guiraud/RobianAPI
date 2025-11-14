"""
Modèles pour les collections et favoris utilisateur
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Boolean, Integer, Text, JSON, ForeignKey, Index, Table, Column, func
from sqlalchemy.dialects.postgresql import ARRAY

from .database import Base


# Table d'association pour les débats dans les collections (many-to-many)
collection_debates = Table(
    "collection_debates",
    Base.metadata,
    Column("collection_id", String(36), ForeignKey("collections.id"), primary_key=True),
    Column("debate_id", String(36), ForeignKey("debates.id"), primary_key=True),
    Index("idx_collection_debates_collection", "collection_id"),
    Index("idx_collection_debates_debate", "debate_id"),
)


class ActivityType(str, Enum):
    """Types d'activité utilisateur"""
    VIEW_DEBATE = "view_debate"
    DOWNLOAD_AUDIO = "download_audio"
    STREAM_AUDIO = "stream_audio"
    ADD_FAVORITE = "add_favorite"
    REMOVE_FAVORITE = "remove_favorite"
    CREATE_COLLECTION = "create_collection"
    ADD_TO_COLLECTION = "add_to_collection"
    SEARCH = "search"


class Collection(Base):
    """Collections personnalisées d'utilisateur"""
    __tablename__ = "collections"
    
    # Identifiant unique
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Informations de base
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Propriétaire (pour l'instant optionnel, à connecter avec auth plus tard)
    user_id: Mapped[Optional[str]] = mapped_column(String(36))
    
    # Configuration
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Métadonnées
    color: Mapped[Optional[str]] = mapped_column(String(20))  # Couleur hex
    icon: Mapped[Optional[str]] = mapped_column(String(50))   # Nom d'icône
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    # Statistiques
    debate_count: Mapped[int] = mapped_column(Integer, default=0)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Métadonnées supplémentaires
    extra_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Relations - sera ajouté quand debates.py importera collections
    # debates: Mapped[List["Debate"]] = relationship(
    #     "Debate",
    #     secondary=collection_debates,
    #     back_populates="collections"
    # )
    
    # Index
    __table_args__ = (
        Index("idx_collections_user", "user_id"),
        Index("idx_collections_public", "is_public"),
        Index("idx_collections_name", "name"),
    )
    
    def __repr__(self):
        return f"<Collection(id={self.id}, name='{self.name}', debates={self.debate_count})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour API"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "is_public": self.is_public,
            "is_default": self.is_default,
            "color": self.color,
            "icon": self.icon,
            "sort_order": self.sort_order,
            "debate_count": self.debate_count,
            "view_count": self.view_count,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Favorite(Base):
    """Débats favoris d'utilisateur"""
    __tablename__ = "favorites"
    
    # Identifiant unique
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Relations
    user_id: Mapped[Optional[str]] = mapped_column(String(36))  # Pour l'instant optionnel
    debate_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("debates.id"), 
        nullable=False
    )
    
    # Métadonnées du favori
    note: Mapped[Optional[str]] = mapped_column(Text)  # Note personnelle
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    
    # Progression (pour les débats longs)
    last_position_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    watch_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Métadonnées
    extra_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Relations
    debate: Mapped["Debate"] = relationship("Debate")
    
    # Index et contraintes
    __table_args__ = (
        Index("idx_favorites_user", "user_id"),
        Index("idx_favorites_debate", "debate_id"),
        Index("idx_favorites_user_debate", "user_id", "debate_id", unique=True),  # Un favori par user/debate
    )
    
    def __repr__(self):
        return f"<Favorite(id={self.id}, user_id={self.user_id}, debate_id={self.debate_id})>"
    
    @property
    def progress_percentage(self) -> Optional[float]:
        """Pourcentage de progression"""
        if not self.last_position_seconds or not self.debate:
            return None
        
        # Utiliser la durée du débat en secondes
        total_seconds = None
        if self.debate.duration_minutes:
            total_seconds = self.debate.duration_minutes * 60
        elif self.debate.audio_files:
            # Prendre la durée du premier fichier audio disponible
            for audio_file in self.debate.audio_files:
                if audio_file.duration_seconds:
                    total_seconds = audio_file.duration_seconds
                    break
        
        if total_seconds:
            return min(100.0, (self.last_position_seconds / total_seconds) * 100)
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour API"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "debate_id": self.debate_id,
            "note": self.note,
            "tags": self.tags,
            "last_position_seconds": self.last_position_seconds,
            "progress_percentage": self.progress_percentage,
            "watch_count": self.watch_count,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class UserActivity(Base):
    """Activité et statistiques utilisateur"""
    __tablename__ = "user_activities"

    # Identifiant unique
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Utilisateur
    user_id: Mapped[Optional[str]] = mapped_column(String(36))
    session_id: Mapped[Optional[str]] = mapped_column(String(36))  # Session anonyme

    # Action effectuée
    action_type: Mapped[ActivityType] = mapped_column(String(50), nullable=False)

    # Contexte de l'action
    debate_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("debates.id"))
    collection_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("collections.id"))

    # Données de l'action
    action_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Métadonnées de contexte
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))  # IPv6 max length
    platform: Mapped[Optional[str]] = mapped_column(String(50))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relations
    debate: Mapped[Optional["Debate"]] = relationship("Debate")
    collection: Mapped[Optional["Collection"]] = relationship("Collection")
    
    # Index
    __table_args__ = (
        Index("idx_activities_user", "user_id"),
        Index("idx_activities_session", "session_id"),
        Index("idx_activities_action", "action_type"),
        Index("idx_activities_debate", "debate_id"),
        Index("idx_activities_created", "created_at"),
    )
    
    def __repr__(self):
        return f"<UserActivity(id={self.id}, action={self.action_type}, user={self.user_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour API"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "action_type": self.action_type.value,
            "debate_id": self.debate_id,
            "collection_id": self.collection_id,
            "action_data": self.action_data,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
            "platform": self.platform,
            "created_at": self.created_at.isoformat(),
        }


class SystemStats(Base):
    """Statistiques système globales"""
    __tablename__ = "system_stats"
    
    # Identifiant unique
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Type de statistique
    stat_type: Mapped[str] = mapped_column(String(100), nullable=False)
    stat_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Valeurs
    count_value: Mapped[Optional[int]] = mapped_column(Integer)
    float_value: Mapped[Optional[float]] = mapped_column()
    json_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    
    # Métadonnées
    extra_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Index
    __table_args__ = (
        Index("idx_system_stats_type", "stat_type"),
        Index("idx_system_stats_date", "stat_date"),
        Index("idx_system_stats_type_date", "stat_type", "stat_date"),
    )
    
    def __repr__(self):
        return f"<SystemStats(type={self.stat_type}, date={self.stat_date}, value={self.count_value or self.float_value})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour API"""
        return {
            "id": self.id,
            "stat_type": self.stat_type,
            "stat_date": self.stat_date.isoformat(),
            "count_value": self.count_value,
            "float_value": self.float_value,
            "json_value": self.json_value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }
