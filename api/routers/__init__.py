"""
Routers pour RobianAPI
"""

from .debates import router as debates_router
from .streaming import router as streaming_router
from .collections import router as collections_router
from .health import router as health_router

__all__ = [
    "debates_router",
    "streaming_router", 
    "collections_router",
    "health_router"
]
