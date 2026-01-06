import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlmodel import select, Session
import uuid

from main import (
    app,
    get_session_id,
    SearchRequest,
    SESSION_COOKIE_NAME,
)
from database import (
    Search,
    Result,
    ArtistCache,
    Track,
    GameSession,
    GameMatch,
    UserSession,
)


class TestRootEndpoint:
    """Tests for root endpoint"""

    def test_root_returns_html(self, client):
        """Test that root endpoint returns HTML"""
        response = client.get("/")
        assert response.status_code == 200


class TestSearchEndpoint:
    """Tests for /search endpoint"""

    @pytest.mark.asyncio
    async def test_search_success(self, client):
        """Test successful artist search"""
        mock_results = [
            {
                "artistId": 12345,
                "artistName": "Test Artist",
                "primaryGenreName": "Rock",
                "primaryGenreId": 21,
                "artworkUrl100": "https://example.com/art.jpg",
                "artistViewUrl": "https://music.apple.com/artist",
            }
        ]

        with patch("main.search_artists", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_results

            response = client.post(
                "/search",
                json={"artist_name": "Test Artist"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 1
            assert data["results"][0]["artist_name"] == "Test Artist"
            assert data["results"][0]["artist_id"] == "12345"

    @pytest.mark.asyncio
    async def test_search_strips_whitespace(self, client):
        """Test that search query is stripped of whitespace"""
        with patch("main.search_artists", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            response = client.post(
                "/search",
                json={"artist_name": "  Test Artist  "}
            )

            assert response.status_code == 200
            mock_search.assert_called_once_with("Test Artist")

    @pytest.mark.asyncio
    async def test_search_empty_results(self, client):
        """Test search with no results"""
        with patch("main.search_artists", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            response = client.post(
                "/search",
                json={"artist_name": "NonexistentArtist"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["results"]) == 0


class TestHistoryEndpoint:
    """Tests for /history endpoint"""

    def test_get_history_with_session(self, client, test_session, sample_user_session, sample_search):
        """Test retrieving search history"""
        with patch("main.get_session_id") as mock_get_session:
            mock_get_session.return_value = sample_user_session.session_id

            response = client.get("/history")

            assert response.status_code == 200
            data = response.json()
            assert len(data["searches"]) == 1
            assert data["searches"][0]["artist_query"] == "Test Artist"

    def test_get_history_without_session(self, client):
        """Test retrieving history without session"""
        with patch("main.get_session_id") as mock_get_session:
            mock_get_session.return_value = None

            response = client.get("/history")

            assert response.status_code == 200
            data = response.json()
            assert len(data["searches"]) == 0


class TestAlbumsEndpoint:
    """Tests for albums endpoints"""

    @pytest.mark.asyncio
    async def test_get_artist_albums_success(self, client):
        """Test successful album retrieval"""
        mock_albums = [
            {
                "collectionId": 67890,
                "collectionName": "Test Album",
                "artistName": "Test Artist",
                "artworkUrl100": "https://example.com/art100.jpg",
                "artworkUrl600": "https://example.com/art600.jpg",
                "primaryGenreName": "Rock",
                "releaseDate": "2024-01-01",
                "trackCount": 12,
                "collectionViewUrl": "https://music.apple.com/album",
                "collectionPrice": 9.99,
                "currency": "USD",
            }
        ]

        with patch("main.search_albums_by_artist", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_albums

            response = client.get("/api/albums/12345")

            assert response.status_code == 200
            data = response.json()
            assert data["artist_id"] == "12345"
            assert data["artist_name"] == "Test Artist"
            assert len(data["albums"]) == 1
            assert data["albums"][0]["collection_name"] == "Test Album"

    @pytest.mark.asyncio
    async def test_get_artist_albums_empty(self, client):
        """Test album retrieval with no results"""
        with patch("main.search_albums_by_artist", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            response = client.get("/api/albums/12345")

            assert response.status_code == 200
            data = response.json()
            assert data["artist_id"] == "12345"
            assert len(data["albums"]) == 0

    @pytest.mark.asyncio
    async def test_get_artist_albums_fallback_artwork(self, client):
        """Test artwork URL fallback when 600px not available"""
        mock_albums = [
            {
                "collectionId": 67890,
                "collectionName": "Test Album",
                "artistName": "Test Artist",
                "artworkUrl100": "https://example.com/art100.jpg",
                # No artworkUrl600
            }
        ]

        with patch("main.search_albums_by_artist", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_albums

            response = client.get("/api/albums/12345")

            assert response.status_code == 200
            data = response.json()
            assert data["albums"][0]["artwork_url_600"] == "https://example.com/art100.jpg"


class TestCollectTracksEndpoints:
    """Tests for track collection endpoints"""

    @pytest.mark.asyncio
    async def test_collect_album_tracks_success(self, client):
        """Test successful track collection"""
        mock_tracks = [
            {
                "artistId": 12345,
                "artistName": "Test Artist",
                "collectionId": 67890,
                "collectionName": "Test Album",
                "trackId": 111,
                "trackNumber": 1,
                "trackName": "Test Song",
                "trackTimeMillis": 180000,
                "previewUrl": "https://example.com/preview.m4a",
                "primaryGenreName": "Rock",
                "artworkUrl600": "https://example.com/art.jpg",
            }
        ]

        with patch("main.get_album_tracks", new_callable=AsyncMock) as mock_get_tracks:
            with patch("main.is_artist_cached") as mock_is_cached:
                mock_is_cached.return_value = False
                mock_get_tracks.return_value = mock_tracks

                response = client.post("/api/collect-album-tracks/12345/67890")

                assert response.status_code == 200
                data = response.json()
                assert data["collection_id"] == "67890"
                assert data["artist_id"] == "12345"
                assert len(data["tracks"]) == 1
                assert data["tracks"][0]["track_name"] == "Test Song"

    @pytest.mark.asyncio
    async def test_collect_album_tracks_already_cached(self, client):
        """Test collecting tracks when already cached"""
        mock_track = MagicMock()
        mock_track.track_id = "111"
        mock_track.track_number = 1
        mock_track.track_name = "Test Song"
        mock_track.track_duration_ms = 180000
        mock_track.preview_url = "https://example.com/preview.m4a"
        mock_track.explicit = False
        mock_track.primary_genre = "Rock"

        with patch("main.is_artist_cached") as mock_is_cached:
            with patch("main.get_artist_tracks") as mock_get_tracks:
                mock_is_cached.return_value = True
                mock_get_tracks.return_value = [mock_track]

                response = client.post("/api/collect-album-tracks/12345/67890")

                assert response.status_code == 200
                data = response.json()
                assert len(data["tracks"]) == 1

    @pytest.mark.asyncio
    async def test_collect_all_artist_tracks_success(self, client):
        """Test collecting all tracks for an artist"""
        mock_albums = [
            {
                "collectionId": 67890,
                "collectionName": "Album 1",
                "artistName": "Test Artist",
                "wrapperType": "collection",
                "collectionType": "Album",
            }
        ]

        mock_tracks = [
            {
                "artistName": "Test Artist",
                "trackId": 111,
                "trackNumber": 1,
                "trackName": "Song 1",
                "trackTimeMillis": 180000,
                "primaryGenreName": "Rock",
                "collectionId": 67890,
                "collectionName": "Album 1",
            }
        ]

        with patch("main.search_albums_by_artist", new_callable=AsyncMock) as mock_albums_search:
            with patch("main.get_album_tracks", new_callable=AsyncMock) as mock_get_tracks:
                mock_albums_search.return_value = mock_albums
                mock_get_tracks.return_value = mock_tracks

                response = client.post("/api/collect-all-artist-tracks/12345")

                assert response.status_code == 200
                data = response.json()
                assert data["artist_id"] == "12345"
                assert data["artist_name"] == "Test Artist"
                assert data["total_albums"] == 1
                assert data["total_tracks_collected"] == 1
                assert data["albums"][0]["new_tracks"] == 1

    @pytest.mark.asyncio
    async def test_collect_all_artist_tracks_skips_duplicates(self, client, test_engine):
        """Test that duplicate tracks are skipped"""
        # First, add a track to the database
        with Session(test_engine) as session:
            existing_track = Track(
                artist_id="12345",
                collection_id="67890",
                track_id="111",
                track_number=1,
                track_name="Existing Song",
                track_duration_ms=180000,
                primary_genre="Rock"
            )
            session.add(existing_track)
            session.commit()

        mock_albums = [
            {
                "collectionId": 67890,
                "collectionName": "Album 1",
                "artistName": "Test Artist",
                "wrapperType": "collection",
                "collectionType": "Album",
            }
        ]

        mock_tracks = [
            {
                "artistName": "Test Artist",
                "trackId": 111,  # Same track ID as existing
                "trackNumber": 1,
                "trackName": "Song 1",
                "trackTimeMillis": 180000,
                "primaryGenreName": "Rock",
                "collectionId": 67890,
                "collectionName": "Album 1",
            }
        ]

        with patch("main.search_albums_by_artist", new_callable=AsyncMock) as mock_albums_search:
            with patch("main.get_album_tracks", new_callable=AsyncMock) as mock_get_tracks:
                mock_albums_search.return_value = mock_albums
                mock_get_tracks.return_value = mock_tracks

                response = client.post("/api/collect-all-artist-tracks/12345")

                assert response.status_code == 200
                data = response.json()
                assert data["albums"][0]["skipped_tracks"] == 1
                assert data["albums"][0]["new_tracks"] == 0


class TestCachedArtistsEndpoints:
    """Tests for cached artists endpoints"""

    def test_get_cached_artists(self, client, test_engine):
        """Test retrieving all cached artists"""
        with Session(test_engine) as session:
            cache = ArtistCache(
                artist_id="12345",
                artist_name="Test Artist",
                tracks_collected=True
            )
            session.add(cache)
            session.commit()

        response = client.get("/api/cached-artists")

        assert response.status_code == 200
        data = response.json()
        assert len(data["artists"]) == 1
        assert data["artists"][0]["artist_id"] == "12345"

    def test_get_artists_with_track_counts(self, client, test_engine):
        """Test retrieving artists with track counts"""
        with Session(test_engine) as session:
            cache = ArtistCache(
                artist_id="12345",
                artist_name="Test Artist",
                tracks_collected=True
            )
            track = Track(
                artist_id="12345",
                collection_id="67890",
                track_id="111",
                track_number=1,
                track_name="Test Song",
                track_duration_ms=180000,
                primary_genre="Rock"
            )
            session.add(cache)
            session.add(track)
            session.commit()

        response = client.get("/api/artists-with-track-counts")

        assert response.status_code == 200
        data = response.json()
        assert data["total_artists"] == 1
        assert data["total_tracks"] == 1
        assert len(data["artists"]) == 1
        assert data["artists"][0]["track_count"] == 1

    def test_get_artist_all_tracks(self, client, test_engine):
        """Test retrieving all tracks for an artist"""
        with Session(test_engine) as session:
            track = Track(
                artist_id="12345",
                collection_id="67890",
                track_id="111",
                track_number=1,
                track_name="Test Song",
                track_duration_ms=180000,
                collection_name="Test Album",
                primary_genre="Rock"
            )
            session.add(track)
            session.commit()

        response = client.get("/api/tracks/12345")

        assert response.status_code == 200
        data = response.json()
        assert data["artist_id"] == "12345"
        assert data["total_tracks"] == 1
        assert data["total_albums"] == 1
        assert len(data["albums"]) == 1
        assert len(data["albums"][0]["tracks"]) == 1

    def test_get_artist_all_tracks_groups_by_album(self, client, test_engine):
        """Test that tracks are grouped by album"""
        with Session(test_engine) as session:
            track1 = Track(
                artist_id="12345", collection_id="67890", track_id="1",
                track_number=1, track_name="Song 1", track_duration_ms=180000,
                collection_name="Album 1", primary_genre="Rock"
            )
            track2 = Track(
                artist_id="12345", collection_id="67890", track_id="2",
                track_number=2, track_name="Song 2", track_duration_ms=200000,
                collection_name="Album 1", primary_genre="Rock"
            )
            track3 = Track(
                artist_id="12345", collection_id="99999", track_id="3",
                track_number=1, track_name="Song 3", track_duration_ms=150000,
                collection_name="Album 2", primary_genre="Rock"
            )

            session.add(track1)
            session.add(track2)
            session.add(track3)
            session.commit()

        response = client.get("/api/tracks/12345")

        assert response.status_code == 200
        data = response.json()
        assert data["total_albums"] == 2
        assert len(data["albums"]) == 2


class TestGameEndpoints:
    """Tests for game endpoints"""

    def test_start_game_success(self, client, test_engine):
        """Test starting a new game"""
        with Session(test_engine) as session:
            # Create user session
            user_session = UserSession(session_id=str(uuid.uuid4()))
            session.add(user_session)

            # Create 8 tracks
            for i in range(8):
                track = Track(
                    artist_id="12345",
                    collection_id="67890",
                    track_id=f"track_{i}",
                    track_number=i + 1,
                    track_name=f"Song {i + 1}",
                    track_duration_ms=180000,
                    artwork_url_600=f"https://example.com/art_{i}.jpg",
                    primary_genre="Rock"
                )
                session.add(track)
            session.commit()
            session_id = user_session.session_id

        with patch("main.get_session_id") as mock_get_session:
            mock_get_session.return_value = session_id

            response = client.post("/api/game/start/12345")

            assert response.status_code == 200
            data = response.json()
            assert "game_id" in data
            assert data["artist_id"] == "12345"
            assert len(data["matches"]) == 4  # 8 tracks = 4 matches
            assert data["round_number"] == 1

    def test_start_game_insufficient_tracks(self, client, test_engine):
        """Test starting game with insufficient tracks"""
        with Session(test_engine) as session:
            user_session = UserSession(session_id=str(uuid.uuid4()))
            session.add(user_session)
            track = Track(
                artist_id="12345",
                collection_id="67890",
                track_id="111",
                track_number=1,
                track_name="Only Song",
                track_duration_ms=180000,
                primary_genre="Rock"
            )
            session.add(track)
            session.commit()
            session_id = user_session.session_id

        with patch("main.get_session_id") as mock_get_session:
            mock_get_session.return_value = session_id

            response = client.post("/api/game/start/12345")

            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert data["available_tracks"] == 1

    def test_record_match_result_round_in_progress(self, client, test_engine):
        """Test recording a match result when round is still in progress"""
        with Session(test_engine) as session:
            user_session = UserSession(session_id=str(uuid.uuid4()))
            session.add(user_session)
            session.commit()

            game = GameSession(
                game_id=str(uuid.uuid4()),
                user_session_id=user_session.session_id,
                artist_id="12345",
                status="active"
            )
            session.add(game)
            session.commit()

            match = GameMatch(
                game_session_id=game.game_id,
                round_number=1,
                match_number=1,
                track_id_1="track1",
                track_name_1="Song 1",
                artwork_url_1="url1",
                track_id_2="track2",
                track_name_2="Song 2",
                artwork_url_2="url2"
            )
            session.add(match)
            session.commit()

            game_id = game.game_id
            match_id = match.id

        response = client.post("/api/game/match-result", json={
            "game_id": game_id,
            "match_id": match_id,
            "winner_track_id": "track1"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "round_in_progress"

    def test_get_game_results_not_completed(self, client, test_engine):
        """Test getting results for incomplete game"""
        with Session(test_engine) as session:
            user_session = UserSession(session_id=str(uuid.uuid4()))
            session.add(user_session)
            session.commit()

            game = GameSession(
                game_id=str(uuid.uuid4()),
                user_session_id=user_session.session_id,
                artist_id="12345",
                status="active"
            )
            session.add(game)
            session.commit()
            game_id = game.game_id

        response = client.get(f"/api/game/results/{game_id}")

        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    def test_get_game_results_not_found(self, client):
        """Test getting results for non-existent game"""
        response = client.get("/api/game/results/nonexistent-game-id")

        assert response.status_code == 200
        data = response.json()
        assert "error" in data


class TestHTMLPageEndpoints:
    """Tests for HTML page serving endpoints"""

    def test_albums_page(self, client):
        """Test albums page endpoint"""
        response = client.get("/albums")
        assert response.status_code == 200

    def test_collected_artists_page(self, client):
        """Test collected artists page endpoint"""
        response = client.get("/collected-artists")
        assert response.status_code == 200

    def test_collected_tracks_page(self, client):
        """Test collected tracks page endpoint"""
        response = client.get("/collected-tracks")
        assert response.status_code == 200

    def test_game_page(self, client):
        """Test game page endpoint"""
        response = client.get("/game")
        assert response.status_code == 200
