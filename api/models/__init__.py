"""
Modèles de données pour RobianAPI
"""

from .database import (
    Base,
    engine,
    AsyncSessionLocal,
    get_session,
    get_db_session,
    init_database,
    close_database,
    DatabaseHealthCheck,
    create_all_tables,
    drop_all_tables
)

from .debates import (
    Debate,
    AudioFile,
    ScheduledSession,
    DebateType,
    DebateStatus
)

from .collections import (
    Collection,
    Favorite,
    UserActivity,
    SystemStats,
    ActivityType,
    collection_debates
)

__all__ = [
    # Database
    "Base",
    "engine", 
    "AsyncSessionLocal",
    "get_session",
    "get_db_session",
    "init_database",
    "close_database",
    "DatabaseHealthCheck",
    "create_all_tables",
    "drop_all_tables",
    
    # Debates
    "Debate",
    "AudioFile", 
    "ScheduledSession",
    "DebateType",
    "DebateStatus",
    
    # Collections
    "Collection",
    "Favorite",
    "UserActivity",
    "SystemStats",
    "ActivityType",
    "collection_debates",
]
