import pytest
from datetime import datetime
from sqlmodel import select
import uuid

from database import (
    UserSession,
    Search,
    Result,
    ArtistCache,
    Track,
    GameSession,
    GameMatch,
    get_or_create_session,
    get_or_create_artist_cache,
    is_artist_cached,
    get_cached_artists,
    get_artist_tracks,
    get_all_artist_tracks,
    create_game_session,
    get_game_session,
    create_game_match,
    record_match_winner,
    get_game_matches,
    get_all_game_matches,
    finish_game_session,
)


class TestUserSessionModel:
    """Tests for UserSession model"""

    def test_create_user_session(self, test_session):
        """Test creating a user session"""
        session_id = str(uuid.uuid4())
        user_session = UserSession(session_id=session_id)

        test_session.add(user_session)
        test_session.commit()
        test_session.refresh(user_session)

        assert user_session.id is not None
        assert user_session.session_id == session_id
        assert isinstance(user_session.created_at, datetime)
        assert isinstance(user_session.updated_at, datetime)

    def test_user_session_unique_constraint(self, test_session):
        """Test that session_id must be unique"""
        session_id = str(uuid.uuid4())

        session1 = UserSession(session_id=session_id)
        test_session.add(session1)
        test_session.commit()

        session2 = UserSession(session_id=session_id)
        test_session.add(session2)

        with pytest.raises(Exception):  # SQLite IntegrityError
            test_session.commit()

    def test_user_session_relationship_with_searches(self, test_session, sample_user_session):
        """Test relationship between UserSession and Search"""
        search = Search(
            session_id=sample_user_session.session_id,
            artist_query="Test Query"
        )
        test_session.add(search)
        test_session.commit()

        # Reload the user session
        test_session.refresh(sample_user_session)

        assert len(sample_user_session.searches) == 1
        assert sample_user_session.searches[0].artist_query == "Test Query"


class TestSearchModel:
    """Tests for Search model"""

    def test_create_search(self, test_session, sample_user_session):
        """Test creating a search"""
        search = Search(
            session_id=sample_user_session.session_id,
            artist_query="Taylor Swift"
        )

        test_session.add(search)
        test_session.commit()
        test_session.refresh(search)

        assert search.id is not None
        assert search.session_id == sample_user_session.session_id
        assert search.artist_query == "Taylor Swift"
        assert isinstance(search.created_at, datetime)

    def test_search_relationship_with_results(self, test_session, sample_search):
        """Test relationship between Search and Result"""
        result = Result(
            search_id=sample_search.id,
            artist_id="12345",
            artist_name="Test Artist",
            primary_genre="Rock",
            primary_genre_id=21,
            artist_type="Artist",
            wrapper_type="artist"
        )
        test_session.add(result)
        test_session.commit()

        test_session.refresh(sample_search)

        assert len(sample_search.results) == 1
        assert sample_search.results[0].artist_name == "Test Artist"


class TestResultModel:
    """Tests for Result model"""

    def test_create_result(self, test_session, sample_search):
        """Test creating a result"""
        result = Result(
            search_id=sample_search.id,
            artist_id="12345",
            artist_name="Test Artist",
            primary_genre="Rock",
            primary_genre_id=21,
            artwork_url_100="https://example.com/art.jpg",
            artist_link_url="https://music.apple.com/artist",
            artist_type="Artist",
            wrapper_type="artist"
        )

        test_session.add(result)
        test_session.commit()
        test_session.refresh(result)

        assert result.id is not None
        assert result.artist_id == "12345"
        assert result.artist_name == "Test Artist"
        assert result.primary_genre == "Rock"


class TestArtistCacheModel:
    """Tests for ArtistCache model"""

    def test_create_artist_cache(self, test_session):
        """Test creating an artist cache entry"""
        cache = ArtistCache(
            artist_id="12345",
            artist_name="Test Artist",
            albums_collected=False,
            tracks_collected=False
        )

        test_session.add(cache)
        test_session.commit()
        test_session.refresh(cache)

        assert cache.id is not None
        assert cache.artist_id == "12345"
        assert cache.artist_name == "Test Artist"
        assert cache.albums_collected is False
        assert cache.tracks_collected is False

    def test_artist_cache_unique_constraint(self, test_session):
        """Test that artist_id must be unique"""
        cache1 = ArtistCache(artist_id="12345", artist_name="Artist")
        test_session.add(cache1)
        test_session.commit()

        cache2 = ArtistCache(artist_id="12345", artist_name="Artist")
        test_session.add(cache2)

        with pytest.raises(Exception):  # SQLite IntegrityError
            test_session.commit()

    def test_update_artist_cache_flags(self, test_session, sample_artist_cache):
        """Test updating cache flags"""
        sample_artist_cache.albums_collected = True
        sample_artist_cache.tracks_collected = True

        test_session.add(sample_artist_cache)
        test_session.commit()
        test_session.refresh(sample_artist_cache)

        assert sample_artist_cache.albums_collected is True
        assert sample_artist_cache.tracks_collected is True


class TestTrackModel:
    """Tests for Track model"""

    def test_create_track(self, test_session):
        """Test creating a track"""
        track = Track(
            artist_id="12345",
            collection_id="67890",
            track_id="111",
            track_number=1,
            track_name="Test Song",
            track_duration_ms=180000,
            preview_url="https://example.com/preview.m4a",
            is_playable=True,
            explicit=False,
            primary_genre="Rock",
            release_date="2024-01-01",
            collection_name="Test Album",
            artwork_url_600="https://example.com/art.jpg"
        )

        test_session.add(track)
        test_session.commit()
        test_session.refresh(track)

        assert track.id is not None
        assert track.artist_id == "12345"
        assert track.collection_id == "67890"
        assert track.track_id == "111"
        assert track.track_name == "Test Song"
        assert track.track_duration_ms == 180000

    def test_track_optional_fields(self, test_session):
        """Test track with optional fields as None"""
        track = Track(
            artist_id="12345",
            collection_id="67890",
            track_id="111",
            track_number=1,
            track_name="Test Song",
            track_duration_ms=180000,
            primary_genre="Rock"
        )

        test_session.add(track)
        test_session.commit()
        test_session.refresh(track)

        assert track.preview_url is None
        assert track.release_date is None
        assert track.collection_name is None


class TestGameSessionModel:
    """Tests for GameSession model"""

    def test_create_game_session(self, test_session, sample_user_session):
        """Test creating a game session"""
        game = GameSession(
            game_id=str(uuid.uuid4()),
            user_session_id=sample_user_session.session_id,
            artist_id="12345",
            status="active",
            total_rounds=3
        )

        test_session.add(game)
        test_session.commit()
        test_session.refresh(game)

        assert game.id is not None
        assert game.status == "active"
        assert game.total_rounds == 3
        assert game.winner_track_id is None

    def test_game_session_relationship_with_matches(self, test_session, sample_game_session, sample_tracks):
        """Test relationship between GameSession and GameMatch"""
        match = GameMatch(
            game_session_id=sample_game_session.game_id,
            round_number=1,
            match_number=1,
            track_id_1=sample_tracks[0].track_id,
            track_name_1=sample_tracks[0].track_name,
            artwork_url_1=sample_tracks[0].artwork_url_600 or "",
            track_id_2=sample_tracks[1].track_id,
            track_name_2=sample_tracks[1].track_name,
            artwork_url_2=sample_tracks[1].artwork_url_600 or ""
        )
        test_session.add(match)
        test_session.commit()

        test_session.refresh(sample_game_session)

        assert len(sample_game_session.matches) == 1


class TestGameMatchModel:
    """Tests for GameMatch model"""

    def test_create_game_match(self, test_session, sample_game_session):
        """Test creating a game match"""
        match = GameMatch(
            game_session_id=sample_game_session.game_id,
            round_number=1,
            match_number=1,
            track_id_1="track1",
            track_name_1="Song 1",
            artwork_url_1="https://example.com/art1.jpg",
            track_id_2="track2",
            track_name_2="Song 2",
            artwork_url_2="https://example.com/art2.jpg"
        )

        test_session.add(match)
        test_session.commit()
        test_session.refresh(match)

        assert match.id is not None
        assert match.round_number == 1
        assert match.match_number == 1
        assert match.winner_track_id is None
        assert match.loser_track_id is None


class TestDatabaseHelperFunctions:
    """Tests for database helper functions"""

    def test_get_or_create_session_creates_new(self, test_session):
        """Test creating a new session"""
        user_session = get_or_create_session(test_session, session_id=None)

        assert user_session.id is not None
        assert user_session.session_id is not None

    def test_get_or_create_session_retrieves_existing(self, test_session, sample_user_session):
        """Test retrieving an existing session"""
        original_id = sample_user_session.id
        original_created_at = sample_user_session.created_at

        retrieved_session = get_or_create_session(test_session, sample_user_session.session_id)

        assert retrieved_session.id == original_id
        assert retrieved_session.created_at == original_created_at
        assert retrieved_session.updated_at > original_created_at

    def test_get_or_create_artist_cache_creates_new(self, test_session):
        """Test creating a new artist cache"""
        cache = get_or_create_artist_cache(test_session, "12345", "Test Artist")

        assert cache.artist_id == "12345"
        assert cache.artist_name == "Test Artist"
        assert cache.albums_collected is False
        assert cache.tracks_collected is False

    def test_get_or_create_artist_cache_retrieves_existing(self, test_session, sample_artist_cache):
        """Test retrieving an existing artist cache"""
        original_id = sample_artist_cache.id

        retrieved_cache = get_or_create_artist_cache(
            test_session,
            sample_artist_cache.artist_id,
            sample_artist_cache.artist_name
        )

        assert retrieved_cache.id == original_id
        assert retrieved_cache.updated_at > sample_artist_cache.created_at

    def test_is_artist_cached_returns_true(self, test_session, sample_artist_cache):
        """Test checking if artist is cached (tracks collected)"""
        sample_artist_cache.tracks_collected = True
        test_session.add(sample_artist_cache)
        test_session.commit()

        is_cached = is_artist_cached(test_session, sample_artist_cache.artist_id)

        assert is_cached is True

    def test_is_artist_cached_returns_false(self, test_session, sample_artist_cache):
        """Test checking if artist is not cached"""
        is_cached = is_artist_cached(test_session, sample_artist_cache.artist_id)

        assert is_cached is False

    def test_get_cached_artists(self, test_session):
        """Test retrieving all cached artists"""
        cache1 = ArtistCache(artist_id="1", artist_name="Artist 1", tracks_collected=True)
        cache2 = ArtistCache(artist_id="2", artist_name="Artist 2", tracks_collected=True)
        cache3 = ArtistCache(artist_id="3", artist_name="Artist 3", tracks_collected=False)

        test_session.add(cache1)
        test_session.add(cache2)
        test_session.add(cache3)
        test_session.commit()

        cached_artists = get_cached_artists(test_session)

        assert len(cached_artists) == 2
        artist_ids = [a.artist_id for a in cached_artists]
        assert "1" in artist_ids
        assert "2" in artist_ids
        assert "3" not in artist_ids

    def test_get_artist_tracks(self, test_session):
        """Test retrieving tracks for a specific artist and collection"""
        track1 = Track(
            artist_id="12345", collection_id="67890", track_id="1",
            track_number=1, track_name="Song 1", track_duration_ms=180000,
            primary_genre="Rock"
        )
        track2 = Track(
            artist_id="12345", collection_id="67890", track_id="2",
            track_number=2, track_name="Song 2", track_duration_ms=200000,
            primary_genre="Rock"
        )
        track3 = Track(
            artist_id="12345", collection_id="99999", track_id="3",
            track_number=1, track_name="Song 3", track_duration_ms=150000,
            primary_genre="Rock"
        )

        test_session.add(track1)
        test_session.add(track2)
        test_session.add(track3)
        test_session.commit()

        tracks = get_artist_tracks(test_session, "12345", "67890")

        assert len(tracks) == 2
        assert tracks[0].track_number == 1
        assert tracks[1].track_number == 2

    def test_get_all_artist_tracks(self, test_session):
        """Test retrieving all tracks for an artist"""
        track1 = Track(
            artist_id="12345", collection_id="67890", track_id="1",
            track_number=1, track_name="Song 1", track_duration_ms=180000,
            primary_genre="Rock"
        )
        track2 = Track(
            artist_id="12345", collection_id="99999", track_id="2",
            track_number=1, track_name="Song 2", track_duration_ms=200000,
            primary_genre="Rock"
        )
        track3 = Track(
            artist_id="54321", collection_id="11111", track_id="3",
            track_number=1, track_name="Song 3", track_duration_ms=150000,
            primary_genre="Rock"
        )

        test_session.add(track1)
        test_session.add(track2)
        test_session.add(track3)
        test_session.commit()

        tracks = get_all_artist_tracks(test_session, "12345")

        assert len(tracks) == 2
        track_ids = [t.track_id for t in tracks]
        assert "1" in track_ids
        assert "2" in track_ids
        assert "3" not in track_ids


class TestGameHelperFunctions:
    """Tests for game-related helper functions"""

    def test_create_game_session_function(self, test_session, sample_user_session):
        """Test create_game_session function"""
        game = create_game_session(test_session, sample_user_session.session_id, "12345")

        assert game.game_id is not None
        assert game.user_session_id == sample_user_session.session_id
        assert game.artist_id == "12345"
        assert game.status == "active"

    def test_get_game_session_function(self, test_session, sample_game_session):
        """Test get_game_session function"""
        retrieved_game = get_game_session(test_session, sample_game_session.game_id)

        assert retrieved_game.id == sample_game_session.id
        assert retrieved_game.game_id == sample_game_session.game_id

    def test_get_game_session_not_found(self, test_session):
        """Test get_game_session with non-existent game"""
        game = get_game_session(test_session, "nonexistent-game-id")

        assert game is None

    def test_create_game_match_function(self, test_session, sample_game_session, sample_tracks):
        """Test create_game_match function"""
        match = create_game_match(
            test_session,
            sample_game_session.game_id,
            round_number=1,
            match_number=1,
            track_1=sample_tracks[0],
            track_2=sample_tracks[1]
        )

        assert match.id is not None
        assert match.game_session_id == sample_game_session.game_id
        assert match.round_number == 1
        assert match.match_number == 1
        assert match.track_id_1 == sample_tracks[0].track_id
        assert match.track_id_2 == sample_tracks[1].track_id

    def test_record_match_winner_function(self, test_session, sample_game_match):
        """Test record_match_winner function"""
        winner_id = sample_game_match.track_id_1

        updated_match = record_match_winner(
            test_session,
            sample_game_match.game_session_id,
            sample_game_match.id,
            winner_id
        )

        assert updated_match.winner_track_id == winner_id
        assert updated_match.loser_track_id == sample_game_match.track_id_2

    def test_record_match_winner_opposite_track(self, test_session, sample_game_match):
        """Test recording winner when track 2 wins"""
        winner_id = sample_game_match.track_id_2

        updated_match = record_match_winner(
            test_session,
            sample_game_match.game_session_id,
            sample_game_match.id,
            winner_id
        )

        assert updated_match.winner_track_id == winner_id
        assert updated_match.loser_track_id == sample_game_match.track_id_1

    def test_get_game_matches_function(self, test_session, sample_game_session, sample_tracks):
        """Test get_game_matches function"""
        match1 = create_game_match(test_session, sample_game_session.game_id, 1, 1, sample_tracks[0], sample_tracks[1])
        match2 = create_game_match(test_session, sample_game_session.game_id, 1, 2, sample_tracks[2], sample_tracks[3])
        match3 = create_game_match(test_session, sample_game_session.game_id, 2, 1, sample_tracks[0], sample_tracks[2])

        round_1_matches = get_game_matches(test_session, sample_game_session.game_id, round_number=1)

        assert len(round_1_matches) == 2
        assert round_1_matches[0].match_number == 1
        assert round_1_matches[1].match_number == 2

    def test_get_all_game_matches_function(self, test_session, sample_game_session, sample_tracks):
        """Test get_all_game_matches function"""
        match1 = create_game_match(test_session, sample_game_session.game_id, 1, 1, sample_tracks[0], sample_tracks[1])
        match2 = create_game_match(test_session, sample_game_session.game_id, 2, 1, sample_tracks[0], sample_tracks[2])

        all_matches = get_all_game_matches(test_session, sample_game_session.game_id)

        assert len(all_matches) == 2
        assert all_matches[0].round_number == 1
        assert all_matches[1].round_number == 2

    def test_finish_game_session_function(self, test_session, sample_game_session, sample_track):
        """Test finish_game_session function"""
        finished_game = finish_game_session(
            test_session,
            sample_game_session.game_id,
            sample_track.track_id
        )

        assert finished_game.status == "completed"
        assert finished_game.winner_track_id == sample_track.track_id
        assert finished_game.winner_track_name == sample_track.track_name
        assert finished_game.winner_artwork_url == sample_track.artwork_url_600

    def test_finish_game_session_not_found(self, test_session):
        """Test finish_game_session with non-existent game"""
        game = finish_game_session(test_session, "nonexistent-game-id", "track-id")

        assert game is None
