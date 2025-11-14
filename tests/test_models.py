"""
Tests for SQLAlchemy models
"""
import pytest
from datetime import datetime, date
from api.models.debates import Debate, DebateType, DebateStatus, AudioFile
from api.models.collections import Collection, Favorite


def test_debate_model_creation():
    """Test creating a Debate model instance"""
    debate = Debate(
        id="test-123",
        title="Test Debate",
        type=DebateType.COMMISSION,
        status=DebateStatus.PROGRAMME,
        date=date(2024, 1, 15),
        source_url="https://example.com/debate/123",
        commission="Test Commission"
    )

    assert debate.id == "test-123"
    assert debate.title == "Test Debate"
    assert debate.type == DebateType.COMMISSION
    assert debate.status == DebateStatus.PROGRAMME
    assert debate.commission == "Test Commission"


def test_debate_enums():
    """Test debate enum values"""
    assert DebateType.COMMISSION == "commission"
    assert DebateType.SEANCE_PUBLIQUE == "seance_publique"
    assert DebateStatus.PROGRAMME == "programme"
    assert DebateStatus.DISPONIBLE == "disponible"


def test_collection_model_creation():
    """Test creating a Collection model instance"""
    collection = Collection(
        id="coll-123",
        name="My Favorites",
        description="My favorite debates",
        is_public=False
    )

    assert collection.id == "coll-123"
    assert collection.name == "My Favorites"
    assert collection.is_public is False


def test_audio_file_model():
    """Test AudioFile model"""
    audio = AudioFile(
        id="audio-123",
        debate_id="debate-123",
        format="mp3",
        quality="192k",
        file_size_mb=45.5
    )

    assert audio.id == "audio-123"
    assert audio.debate_id == "debate-123"
    assert audio.format == "mp3"
    assert audio.quality == "192k"
