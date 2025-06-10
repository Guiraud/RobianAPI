"""
Schémas Pydantic pour RobianAPI
"""

from .debates import (
    DebateTypeSchema,
    DebateStatusSchema,
    DebateBase,
    DebateCreate,
    DebateUpdate,
    AudioFileSchema,
    DebateResponse,
    DebateListResponse,
    DebateSearchFilters,
    ScheduledSessionCreate,
    ScheduledSessionResponse,
    ExtractionRequest,
    ExtractionResponse,
    StreamingInfoResponse,
    DebateStatsResponse
)

__all__ = [
    "DebateTypeSchema",
    "DebateStatusSchema", 
    "DebateBase",
    "DebateCreate",
    "DebateUpdate",
    "AudioFileSchema",
    "DebateResponse",
    "DebateListResponse",
    "DebateSearchFilters",
    "ScheduledSessionCreate",
    "ScheduledSessionResponse",
    "ExtractionRequest",
    "ExtractionResponse",
    "StreamingInfoResponse",
    "DebateStatsResponse"
]
