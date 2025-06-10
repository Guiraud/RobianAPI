"""
Services pour RobianAPI
"""

from .cache_service import (
    cache_service,
    cache_debates,
    get_cached_debates,
    cache_streaming,
    get_cached_streaming,
    cache_metadata,
    get_cached_metadata,
    cached
)

from .websocket_service import (
    websocket_manager,
    WebSocketMessage,
    MessageType,
    ChannelType,
    notify_debate_started,
    notify_debate_ended,
    notify_extraction_started,
    notify_extraction_completed,
    notify_extraction_failed,
    notify_system_status,
    WebSocketMiddleware
)

__all__ = [
    # Cache
    "cache_service",
    "cache_debates",
    "get_cached_debates", 
    "cache_streaming",
    "get_cached_streaming",
    "cache_metadata",
    "get_cached_metadata",
    "cached",
    
    # WebSockets
    "websocket_manager",
    "WebSocketMessage",
    "MessageType",
    "ChannelType",
    "notify_debate_started",
    "notify_debate_ended",
    "notify_extraction_started",
    "notify_extraction_completed",
    "notify_extraction_failed",
    "notify_system_status",
    "WebSocketMiddleware"
]
