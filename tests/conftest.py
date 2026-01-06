import pytest
from sqlmodel import SQLModel, create_engine, Session
from fastapi.testclient import TestClient
from datetime import datetime
import uuid

from database import (
    UserSession,
    Search,
    Result,
    ArtistCache,
    Track,
    GameSession,
    GameMatch,
)
from main import app


@pytest.fixture(name="test_engine")
def test_engine_fixture():
    """Create a test database engine using in-memory SQLite"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(name="test_session")
def test_session_fixture(test_engine):
    """Create a test database session"""
    with Session(test_engine) as session:
        yield session
        session.rollback()


@pytest.fixture(name="client")
def client_fixture(test_engine):
    """Create a test client for FastAPI"""
    def override_get_session():
        with Session(test_engine) as session:
            yield session

    from main import get_session
    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_session(test_session):
    """Create a sample user session for testing"""
    user_session = UserSession(
        session_id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_session.add(user_session)
    test_session.commit()
    test_session.refresh(user_session)
    return user_session


@pytest.fixture
def sample_search(test_session, sample_user_session):
    """Create a sample search for testing"""
    search = Search(
        session_id=sample_user_session.session_id,
        artist_query="Test Artist",
        created_at=datetime.utcnow(),
    )
    test_session.add(search)
    test_session.commit()
    test_session.refresh(search)
    return search


@pytest.fixture
def sample_result(test_session, sample_search):
    """Create a sample result for testing"""
    result = Result(
        search_id=sample_search.id,
        artist_id="12345",
        artist_name="Test Artist",
        primary_genre="Rock",
        primary_genre_id=21,
        artwork_url_100="https://example.com/artwork.jpg",
        artwork_url_60="https://example.com/artwork_60.jpg",
        artist_link_url="https://music.apple.com/artist",
        artist_type="Artist",
        wrapper_type="artist",
        created_at=datetime.utcnow(),
    )
    test_session.add(result)
    test_session.commit()
    test_session.refresh(result)
    return result


@pytest.fixture
def sample_artist_cache(test_session):
    """Create a sample artist cache for testing"""
    cache = ArtistCache(
        artist_id="12345",
        artist_name="Test Artist",
        albums_collected=False,
        tracks_collected=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_session.add(cache)
    test_session.commit()
    test_session.refresh(cache)
    return cache


@pytest.fixture
def sample_track(test_session):
    """Create a sample track for testing"""
    track = Track(
        artist_id="12345",
        collection_id="67890",
        track_id="11111",
        track_number=1,
        track_name="Test Song",
        track_duration_ms=180000,
        preview_url="https://example.com/preview.m4a",
        is_playable=True,
        explicit=False,
        primary_genre="Rock",
        release_date="2024-01-01",
        collection_name="Test Album",
        artwork_url_600="https://example.com/artwork_600.jpg",
        created_at=datetime.utcnow(),
    )
    test_session.add(track)
    test_session.commit()
    test_session.refresh(track)
    return track


@pytest.fixture
def sample_tracks(test_session):
    """Create multiple sample tracks for testing game logic"""
    tracks = []
    for i in range(8):
        track = Track(
            artist_id="12345",
            collection_id="67890",
            track_id=f"track_{i}",
            track_number=i + 1,
            track_name=f"Test Song {i + 1}",
            track_duration_ms=180000 + (i * 10000),
            preview_url=f"https://example.com/preview_{i}.m4a",
            is_playable=True,
            explicit=False,
            primary_genre="Rock",
            release_date="2024-01-01",
            collection_name="Test Album",
            artwork_url_600=f"https://example.com/artwork_{i}.jpg",
            created_at=datetime.utcnow(),
        )
        test_session.add(track)
        tracks.append(track)

    test_session.commit()
    for track in tracks:
        test_session.refresh(track)
    return tracks


@pytest.fixture
def sample_game_session(test_session, sample_user_session):
    """Create a sample game session for testing"""
    game = GameSession(
        game_id=str(uuid.uuid4()),
        user_session_id=sample_user_session.session_id,
        artist_id="12345",
        status="active",
        total_rounds=3,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_session.add(game)
    test_session.commit()
    test_session.refresh(game)
    return game


@pytest.fixture
def sample_game_match(test_session, sample_game_session, sample_tracks):
    """Create a sample game match for testing"""
    match = GameMatch(
        game_session_id=sample_game_session.game_id,
        round_number=1,
        match_number=1,
        track_id_1=sample_tracks[0].track_id,
        track_name_1=sample_tracks[0].track_name,
        artwork_url_1=sample_tracks[0].artwork_url_600 or "",
        track_id_2=sample_tracks[1].track_id,
        track_name_2=sample_tracks[1].track_name,
        artwork_url_2=sample_tracks[1].artwork_url_600 or "",
        created_at=datetime.utcnow(),
    )
    test_session.add(match)
    test_session.commit()
    test_session.refresh(match)
    return match
