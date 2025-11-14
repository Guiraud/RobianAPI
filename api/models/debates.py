"""
Modèles de données pour les débats de l'Assemblée nationale
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Date, DateTime, Boolean, Integer, Text, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from .database import Base


class DebateType(str, Enum):
    """Types de débats"""
    SEANCE_PUBLIQUE = "seance_publique"
    COMMISSION = "commission"
    AUDITION = "audition"
    QUESTION_GOUVERNEMENT = "question_gouvernement"
    AUTRE = "autre"


class DebateStatus(str, Enum):
    """Statuts des débats"""
    PROGRAMME = "programme"          # À venir
    EN_COURS = "en_cours"           # Live
    TERMINE = "termine"             # Fini
    DISPONIBLE = "disponible"      # Audio disponible
    EXTRACTION = "extraction"      # En cours d'extraction
    ERREUR = "erreur"              # Erreur


class Debate(Base):
    """Modèle principal pour un débat"""
    __tablename__ = "debates"
    
    # Identifiant unique
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Informations de base
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Type et statut
    type: Mapped[DebateType] = mapped_column(String(50), nullable=False)
    status: Mapped[DebateStatus] = mapped_column(String(50), default=DebateStatus.PROGRAMME)
    
    # Dates et durée
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    
    # URLs et références
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    video_url: Mapped[Optional[str]] = mapped_column(String(1000))
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1000))
    
    # Commission et salle
    commission: Mapped[Optional[str]] = mapped_column(String(200))
    salle: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Intervenants et participants
    speakers: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    ministers: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    
    # Tags et mots-clés
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    keywords: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    
    # Métadonnées supplémentaires
    extra_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Statistiques
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relations
    audio_files: Mapped[List["AudioFile"]] = relationship(
        "AudioFile", 
        back_populates="debate",
        cascade="all, delete-orphan"
    )
    
    # Index pour les recherches
    __table_args__ = (
        Index("idx_debates_date", "date"),
        Index("idx_debates_type", "type"),
        Index("idx_debates_status", "status"),
        Index("idx_debates_commission", "commission"),
        Index("idx_debates_search", "title", "description"),  # Index texte
        Index("idx_debates_speakers", "speakers"),  # Index array
    )
    
    def __repr__(self):
        return f"<Debate(id={self.id}, title='{self.title[:50]}...', date={self.date})>"
    
    @property
    def is_live(self) -> bool:
        """Vérifier si le débat est en cours"""
        return self.status == DebateStatus.EN_COURS
    
    @property
    def has_audio(self) -> bool:
        """Vérifier si le débat a des fichiers audio"""
        return bool(self.audio_files and any(af.is_ready for af in self.audio_files))
    
    @property
    def display_duration(self) -> str:
        """Durée formatée pour affichage"""
        if not self.duration_minutes:
            return "Durée inconnue"
        
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        
        if hours > 0:
            return f"{hours}h {minutes}min"
        return f"{minutes}min"
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour API"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.type.value,
            "status": self.status.value,
            "date": self.date.isoformat(),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "display_duration": self.display_duration,
            "source_url": self.source_url,
            "video_url": self.video_url,
            "thumbnail_url": self.thumbnail_url,
            "commission": self.commission,
            "salle": self.salle,
            "speakers": self.speakers,
            "ministers": self.ministers,
            "tags": self.tags,
            "keywords": self.keywords,
            "is_live": self.is_live,
            "has_audio": self.has_audio,
            "view_count": self.view_count,
            "download_count": self.download_count,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class AudioFile(Base):
    """Fichiers audio extraits des débats"""
    __tablename__ = "audio_files"
    
    # Identifiant unique
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Relation avec le débat
    debate_id: Mapped[str] = mapped_column(
        String(36), 
        ForeignKey("debates.id"), 
        nullable=False
    )
    
    # Informations du fichier
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # en octets
    
    # Format et qualité
    format: Mapped[str] = mapped_column(String(10), default="mp3")  # mp3, aac, wav
    quality: Mapped[str] = mapped_column(String(20), default="192k")  # bitrate
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Statut de l'extraction
    extraction_status: Mapped[str] = mapped_column(String(50), default="pending")
    extraction_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    extraction_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    extraction_error: Mapped[Optional[str]] = mapped_column(Text)
    
    # URL de streaming et téléchargement
    stream_url: Mapped[Optional[str]] = mapped_column(String(1000))
    download_url: Mapped[Optional[str]] = mapped_column(String(1000))
    
    # Métadonnées audio
    extra_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Statistiques
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    stream_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relations
    debate: Mapped["Debate"] = relationship("Debate", back_populates="audio_files")
    
    # Index
    __table_args__ = (
        Index("idx_audio_debate_id", "debate_id"),
        Index("idx_audio_status", "extraction_status"),
        Index("idx_audio_format", "format"),
    )
    
    def __repr__(self):
        return f"<AudioFile(id={self.id}, debate_id={self.debate_id}, status={self.extraction_status})>"
    
    @property
    def is_ready(self) -> bool:
        """Vérifier si le fichier audio est prêt"""
        return self.extraction_status == "completed"
    
    @property
    def is_extracting(self) -> bool:
        """Vérifier si l'extraction est en cours"""
        return self.extraction_status == "extracting"
    
    @property
    def has_error(self) -> bool:
        """Vérifier s'il y a eu une erreur"""
        return self.extraction_status == "error"
    
    @property
    def file_size_mb(self) -> float:
        """Taille du fichier en MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def duration_formatted(self) -> str:
        """Durée formatée"""
        if not self.duration_seconds:
            return "Durée inconnue"
        
        hours = self.duration_seconds // 3600
        minutes = (self.duration_seconds % 3600) // 60
        seconds = self.duration_seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour API"""
        return {
            "id": self.id,
            "debate_id": self.debate_id,
            "filename": self.filename,
            "file_size": self.file_size,
            "file_size_mb": self.file_size_mb,
            "format": self.format,
            "quality": self.quality,
            "duration_seconds": self.duration_seconds,
            "duration_formatted": self.duration_formatted,
            "extraction_status": self.extraction_status,
            "extraction_started_at": self.extraction_started_at.isoformat() if self.extraction_started_at else None,
            "extraction_completed_at": self.extraction_completed_at.isoformat() if self.extraction_completed_at else None,
            "extraction_error": self.extraction_error,
            "stream_url": self.stream_url,
            "download_url": self.download_url,
            "download_count": self.download_count,
            "stream_count": self.stream_count,
            "is_ready": self.is_ready,
            "is_extracting": self.is_extracting,
            "has_error": self.has_error,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class ScheduledSession(Base):
    """Sessions programmées (programme des séances)"""
    __tablename__ = "scheduled_sessions"
    
    # Identifiant unique
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Informations de base
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[str] = mapped_column(String(10), nullable=False)  # HH:MM
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Type et classification
    type: Mapped[DebateType] = mapped_column(String(50), nullable=False)
    commission: Mapped[Optional[str]] = mapped_column(String(200))
    salle: Mapped[Optional[str]] = mapped_column(String(100))
    
    # URLs
    url: Mapped[Optional[str]] = mapped_column(String(1000))
    live_url: Mapped[Optional[str]] = mapped_column(String(1000))
    
    # Métadonnées
    description: Mapped[Optional[str]] = mapped_column(Text)
    extra_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    
    # Index
    __table_args__ = (
        Index("idx_sessions_date", "date"),
        Index("idx_sessions_type", "type"),
        Index("idx_sessions_commission", "commission"),
    )
    
    def __repr__(self):
        return f"<ScheduledSession(id={self.id}, date={self.date}, title='{self.title[:50]}...')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour API"""
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "start_time": self.start_time,
            "title": self.title,
            "type": self.type.value,
            "commission": self.commission,
            "salle": self.salle,
            "url": self.url,
            "live_url": self.live_url,
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
