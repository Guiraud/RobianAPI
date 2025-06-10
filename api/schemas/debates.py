"""
Schémas Pydantic pour les débats
Validation et sérialisation des données API
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum

from pydantic import BaseModel, Field, validator, ConfigDict
from pydantic.types import constr, conint


class DebateTypeSchema(str, Enum):
    """Types de débats"""
    SEANCE_PUBLIQUE = "seance_publique"
    COMMISSION = "commission"
    AUDITION = "audition"
    QUESTION_GOUVERNEMENT = "question_gouvernement"
    AUTRE = "autre"


class DebateStatusSchema(str, Enum):
    """Statuts des débats"""
    PROGRAMME = "programme"
    EN_COURS = "en_cours"
    TERMINE = "termine"
    DISPONIBLE = "disponible"
    EXTRACTION = "extraction"
    ERREUR = "erreur"


class DebateBase(BaseModel):
    """Schéma de base pour un débat"""
    title: constr(min_length=1, max_length=500) = Field(..., description="Titre du débat")
    description: Optional[str] = Field(None, description="Description détaillée")
    type: DebateTypeSchema = Field(..., description="Type de débat")
    date: date = Field(..., description="Date du débat")
    source_url: str = Field(..., description="URL source du débat")
    
    # Optionnels
    start_time: Optional[datetime] = Field(None, description="Heure de début")
    end_time: Optional[datetime] = Field(None, description="Heure de fin") 
    duration_minutes: Optional[conint(ge=0)] = Field(None, description="Durée en minutes")
    video_url: Optional[str] = Field(None, description="URL de la vidéo")
    thumbnail_url: Optional[str] = Field(None, description="URL de la miniature")
    commission: Optional[str] = Field(None, description="Commission concernée")
    salle: Optional[str] = Field(None, description="Salle du débat")
    speakers: List[str] = Field(default=[], description="Liste des intervenants")
    ministers: List[str] = Field(default=[], description="Liste des ministres")
    tags: List[str] = Field(default=[], description="Tags associés")
    keywords: List[str] = Field(default=[], description="Mots-clés")
    metadata: Dict[str, Any] = Field(default={}, description="Métadonnées supplémentaires")
    
    @validator('source_url', 'video_url', 'thumbnail_url')
    def validate_urls(cls, v):
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    @validator('speakers', 'ministers', 'tags', 'keywords')
    def validate_lists(cls, v):
        # Nettoyer et dédupliquer les listes
        if v:
            return list(set(item.strip() for item in v if item and item.strip()))
        return []


class DebateCreate(DebateBase):
    """Schéma pour créer un débat"""
    status: DebateStatusSchema = Field(default=DebateStatusSchema.PROGRAMME)


class DebateUpdate(BaseModel):
    """Schéma pour mettre à jour un débat"""
    title: Optional[constr(min_length=1, max_length=500)] = None
    description: Optional[str] = None
    type: Optional[DebateTypeSchema] = None
    status: Optional[DebateStatusSchema] = None
    date: Optional[date] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[conint(ge=0)] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    commission: Optional[str] = None
    salle: Optional[str] = None
    speakers: Optional[List[str]] = None
    ministers: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class AudioFileSchema(BaseModel):
    """Schéma pour un fichier audio"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    debate_id: str
    filename: str
    file_size: int
    file_size_mb: float
    format: str
    quality: str
    duration_seconds: Optional[int]
    duration_formatted: str
    extraction_status: str
    extraction_started_at: Optional[datetime]
    extraction_completed_at: Optional[datetime]
    extraction_error: Optional[str]
    stream_url: Optional[str]
    download_url: Optional[str]
    download_count: int
    stream_count: int
    is_ready: bool
    is_extracting: bool
    has_error: bool
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DebateResponse(DebateBase):
    """Schéma de réponse pour un débat"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    status: DebateStatusSchema
    display_duration: str
    is_live: bool
    has_audio: bool
    view_count: int
    download_count: int
    audio_files: List[AudioFileSchema] = []
    created_at: datetime
    updated_at: datetime


class DebateListResponse(BaseModel):
    """Schéma de réponse pour une liste de débats"""
    debates: List[DebateResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class DebateSearchFilters(BaseModel):
    """Filtres de recherche pour les débats"""
    q: Optional[str] = Field(None, description="Recherche textuelle")
    type: Optional[DebateTypeSchema] = Field(None, description="Type de débat")
    status: Optional[DebateStatusSchema] = Field(None, description="Statut du débat")
    commission: Optional[str] = Field(None, description="Commission")
    date_start: Optional[date] = Field(None, description="Date de début")
    date_end: Optional[date] = Field(None, description="Date de fin")
    has_audio: Optional[bool] = Field(None, description="Avec fichiers audio disponibles")
    speakers: Optional[List[str]] = Field(None, description="Intervenants")
    tags: Optional[List[str]] = Field(None, description="Tags")
    
    # Pagination
    page: conint(ge=1) = Field(1, description="Numéro de page")
    per_page: conint(ge=1, le=100) = Field(20, description="Éléments par page")
    
    # Tri
    sort_by: Optional[str] = Field("date", description="Champ de tri")
    sort_order: Optional[str] = Field("desc", description="Ordre de tri (asc/desc)")
    
    @validator('sort_order')
    def validate_sort_order(cls, v):
        if v not in ['asc', 'desc']:
            raise ValueError('sort_order must be "asc" or "desc"')
        return v
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        allowed_fields = ['date', 'title', 'created_at', 'updated_at', 'view_count', 'duration_minutes']
        if v not in allowed_fields:
            raise ValueError(f'sort_by must be one of: {", ".join(allowed_fields)}')
        return v


class ScheduledSessionCreate(BaseModel):
    """Schéma pour créer une session programmée"""
    date: date = Field(..., description="Date de la session")
    start_time: constr(regex=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$') = Field(..., description="Heure de début (HH:MM)")
    title: constr(min_length=1, max_length=500) = Field(..., description="Titre de la session")
    type: DebateTypeSchema = Field(..., description="Type de session")
    commission: Optional[str] = Field(None, description="Commission")
    salle: Optional[str] = Field(None, description="Salle")
    url: Optional[str] = Field(None, description="URL de la session")
    live_url: Optional[str] = Field(None, description="URL du live")
    description: Optional[str] = Field(None, description="Description")
    metadata: Dict[str, Any] = Field(default={}, description="Métadonnées")


class ScheduledSessionResponse(ScheduledSessionCreate):
    """Schéma de réponse pour une session programmée"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    created_at: datetime
    updated_at: datetime


class ExtractionRequest(BaseModel):
    """Demande d'extraction audio"""
    debate_id: str = Field(..., description="ID du débat")
    priority: str = Field("normal", description="Priorité de l'extraction")
    format: str = Field("mp3", description="Format audio souhaité")
    quality: str = Field("192k", description="Qualité audio")
    
    @validator('priority')
    def validate_priority(cls, v):
        if v not in ['low', 'normal', 'high', 'urgent']:
            raise ValueError('priority must be one of: low, normal, high, urgent')
        return v
    
    @validator('format')
    def validate_format(cls, v):
        if v not in ['mp3', 'aac', 'wav']:
            raise ValueError('format must be one of: mp3, aac, wav')
        return v


class ExtractionResponse(BaseModel):
    """Réponse d'extraction audio"""
    extraction_id: str
    debate_id: str
    status: str
    message: str
    estimated_duration: Optional[str] = None
    progress: Optional[int] = None
    error: Optional[str] = None
    audio_file: Optional[AudioFileSchema] = None


class StreamingInfoResponse(BaseModel):
    """Informations de streaming"""
    debate_id: str
    audio_available: bool
    stream_url: Optional[str] = None
    download_url: Optional[str] = None
    file_size: Optional[int] = None
    duration_seconds: Optional[int] = None
    format: Optional[str] = None
    quality: Optional[str] = None
    extraction_status: Optional[str] = None
    message: str


class DebateStatsResponse(BaseModel):
    """Statistiques d'un débat"""
    debate_id: str
    view_count: int
    download_count: int
    stream_count: int
    favorite_count: int
    in_collections_count: int
    average_watch_time: Optional[float] = None
    completion_rate: Optional[float] = None
