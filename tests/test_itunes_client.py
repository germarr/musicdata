import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from itunes_client import (
    search_artists,
    search_albums_by_artist,
    get_album_tracks,
    extract_artist_fields,
    extract_album_fields,
    extract_track_fields,
    ITUNES_API_BASE,
)


class TestSearchArtists:
    """Tests for search_artists function"""

    @pytest.mark.asyncio
    async def test_search_artists_success(self):
        """Test successful artist search with deduplication"""
        mock_response = {
            "resultCount": 3,
            "results": [
                {
                    "artistId": 12345,
                    "artistName": "Test Artist",
                    "primaryGenreName": "Rock",
                    "primaryGenreId": 21,
                    "artworkUrl100": "https://example.com/art.jpg",
                    "artistViewUrl": "https://music.apple.com/artist",
                },
                {
                    "artistId": 12345,  # Duplicate
                    "artistName": "Test Artist",
                    "primaryGenreName": "Rock",
                    "primaryGenreId": 21,
                },
                {
                    "artistId": 67890,
                    "artistName": "Another Artist",
                    "primaryGenreName": "Pop",
                    "primaryGenreId": 14,
                },
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()

            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response_obj)
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            results = await search_artists("Test Artist")

            assert len(results) == 2  # Deduplicated
            assert results[0]["artistId"] == 12345
            assert results[1]["artistId"] == 67890
            mock_client_instance.get.assert_called_once_with(
                f"{ITUNES_API_BASE}/search",
                params={"term": "Test Artist", "limit": 200}
            )

    @pytest.mark.asyncio
    async def test_search_artists_with_custom_limit(self):
        """Test artist search with custom limit"""
        mock_response = {"resultCount": 0, "results": []}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()

            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response_obj)
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            results = await search_artists("Test", limit=50)

            mock_client_instance.get.assert_called_once_with(
                f"{ITUNES_API_BASE}/search",
                params={"term": "Test", "limit": 50}
            )

    @pytest.mark.asyncio
    async def test_search_artists_filters_missing_data(self):
        """Test that results without artist ID or name are filtered out"""
        mock_response = {
            "results": [
                {"artistId": 12345, "artistName": "Valid Artist"},
                {"artistId": None, "artistName": "No ID"},  # Should be filtered
                {"artistId": 67890, "artistName": ""},  # Should be filtered
                {"artistName": "No Artist ID"},  # Should be filtered
                {"artistId": 99999, "artistName": "Another Valid"},
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()

            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response_obj)
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            results = await search_artists("Test")

            assert len(results) == 2
            assert results[0]["artistId"] == 12345
            assert results[1]["artistId"] == 99999

    @pytest.mark.asyncio
    async def test_search_artists_http_error(self):
        """Test handling of HTTP errors"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(side_effect=httpx.HTTPError("API Error"))
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            results = await search_artists("Test")

            assert results == []

    @pytest.mark.asyncio
    async def test_search_artists_empty_response(self):
        """Test handling of empty results"""
        mock_response = {"resultCount": 0, "results": []}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()

            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response_obj)
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            results = await search_artists("NonexistentArtist")

            assert results == []


class TestSearchAlbumsByArtist:
    """Tests for search_albums_by_artist function"""

    @pytest.mark.asyncio
    async def test_search_albums_success(self):
        """Test successful album search"""
        mock_response = {
            "results": [
                {"wrapperType": "artist", "artistId": 12345},  # Should be filtered
                {
                    "wrapperType": "collection",
                    "collectionType": "Album",
                    "collectionId": 67890,
                    "collectionName": "Test Album",
                },
                {
                    "wrapperType": "collection",
                    "collectionType": "Album",
                    "collectionId": 11111,
                    "collectionName": "Another Album",
                },
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()

            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response_obj)
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            albums = await search_albums_by_artist(12345)

            assert len(albums) == 2
            assert albums[0]["collectionId"] == 67890
            assert albums[1]["collectionId"] == 11111
            mock_client_instance.get.assert_called_once_with(
                f"{ITUNES_API_BASE}/lookup",
                params={"id": 12345, "entity": "album", "limit": 50}
            )

    @pytest.mark.asyncio
    async def test_search_albums_filters_non_albums(self):
        """Test that only albums are returned"""
        mock_response = {
            "results": [
                {"wrapperType": "collection", "collectionType": "Album", "collectionId": 1},
                {"wrapperType": "collection", "collectionType": "Compilation", "collectionId": 2},
                {"wrapperType": "track", "collectionId": 3},
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()

            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response_obj)
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            albums = await search_albums_by_artist(12345)

            assert len(albums) == 1
            assert albums[0]["collectionId"] == 1

    @pytest.mark.asyncio
    async def test_search_albums_http_error(self):
        """Test handling of HTTP errors"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(side_effect=httpx.HTTPError("API Error"))
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            albums = await search_albums_by_artist(12345)

            assert albums == []


class TestGetAlbumTracks:
    """Tests for get_album_tracks function"""

    @pytest.mark.asyncio
    async def test_get_tracks_success(self):
        """Test successful track retrieval"""
        mock_response = {
            "results": [
                {"wrapperType": "collection", "collectionId": 67890},  # Filtered
                {
                    "wrapperType": "track",
                    "kind": "song",
                    "trackId": 111,
                    "trackName": "Song 1",
                },
                {
                    "wrapperType": "track",
                    "kind": "song",
                    "trackId": 222,
                    "trackName": "Song 2",
                },
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()

            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response_obj)
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            tracks = await get_album_tracks(67890)

            assert len(tracks) == 2
            assert tracks[0]["trackId"] == 111
            assert tracks[1]["trackId"] == 222
            mock_client_instance.get.assert_called_once_with(
                f"{ITUNES_API_BASE}/lookup",
                params={"id": 67890, "entity": "song", "limit": 200}
            )

    @pytest.mark.asyncio
    async def test_get_tracks_filters_non_songs(self):
        """Test that only songs are returned"""
        mock_response = {
            "results": [
                {"wrapperType": "track", "kind": "song", "trackId": 1},
                {"wrapperType": "track", "kind": "music-video", "trackId": 2},
                {"wrapperType": "collection", "trackId": 3},
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_response_obj.raise_for_status = MagicMock()

            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response_obj)
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            tracks = await get_album_tracks(67890)

            assert len(tracks) == 1
            assert tracks[0]["trackId"] == 1

    @pytest.mark.asyncio
    async def test_get_tracks_http_error(self):
        """Test handling of HTTP errors"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = MagicMock()
            mock_client_instance.get = AsyncMock(side_effect=httpx.HTTPError("API Error"))
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            tracks = await get_album_tracks(67890)

            assert tracks == []


class TestExtractArtistFields:
    """Tests for extract_artist_fields function"""

    def test_extract_complete_data(self):
        """Test extraction with all fields present"""
        result = {
            "artistId": 12345,
            "artistName": "Test Artist",
            "primaryGenreName": "Rock",
            "primaryGenreId": 21,
            "artworkUrl100": "https://example.com/art100.jpg",
            "artworkUrl60": "https://example.com/art60.jpg",
            "artistViewUrl": "https://music.apple.com/artist",
        }

        extracted = extract_artist_fields(result)

        assert extracted["artist_id"] == "12345"
        assert extracted["artist_name"] == "Test Artist"
        assert extracted["primary_genre"] == "Rock"
        assert extracted["primary_genre_id"] == 21
        assert extracted["artwork_url_100"] == "https://example.com/art100.jpg"
        assert extracted["artwork_url_60"] == "https://example.com/art60.jpg"
        assert extracted["artist_link_url"] == "https://music.apple.com/artist"
        assert extracted["artist_type"] == "Artist"
        assert extracted["wrapper_type"] == "artist"

    def test_extract_with_fallback_url(self):
        """Test URL fallback when artistViewUrl is missing"""
        result = {
            "artistId": 12345,
            "artistName": "Test Artist",
            "trackViewUrl": "https://music.apple.com/track",
        }

        extracted = extract_artist_fields(result)

        assert extracted["artist_link_url"] == "https://music.apple.com/track"

    def test_extract_with_missing_fields(self):
        """Test extraction with missing optional fields"""
        result = {
            "artistId": 12345,
            "artistName": "Test Artist",
        }

        extracted = extract_artist_fields(result)

        assert extracted["artist_id"] == "12345"
        assert extracted["artist_name"] == "Test Artist"
        assert extracted["primary_genre"] == "Unknown"
        assert extracted["primary_genre_id"] == 0
        assert extracted["artwork_url_100"] == ""
        assert extracted["artist_link_url"] == ""

    def test_extract_empty_result(self):
        """Test extraction with empty result"""
        result = {}

        extracted = extract_artist_fields(result)

        assert extracted["artist_id"] == ""
        assert extracted["artist_name"] == ""
        assert extracted["primary_genre"] == "Unknown"


class TestExtractAlbumFields:
    """Tests for extract_album_fields function"""

    def test_extract_complete_album_data(self):
        """Test extraction with all album fields"""
        result = {
            "collectionId": 67890,
            "collectionName": "Test Album",
            "artistName": "Test Artist",
            "artistId": 12345,
            "artworkUrl100": "https://example.com/art100.jpg",
            "artworkUrl600": "https://example.com/art600.jpg",
            "primaryGenreName": "Rock",
            "releaseDate": "2024-01-01T00:00:00Z",
            "copyright": "© 2024 Test Records",
            "trackCount": 12,
            "collectionViewUrl": "https://music.apple.com/album",
            "collectionPrice": 9.99,
            "currency": "USD",
        }

        extracted = extract_album_fields(result)

        assert extracted["collection_id"] == "67890"
        assert extracted["collection_name"] == "Test Album"
        assert extracted["artist_name"] == "Test Artist"
        assert extracted["artist_id"] == "12345"
        assert extracted["artwork_url_100"] == "https://example.com/art100.jpg"
        assert extracted["artwork_url_600"] == "https://example.com/art600.jpg"
        assert extracted["primary_genre"] == "Rock"
        assert extracted["release_date"] == "2024-01-01T00:00:00Z"
        assert extracted["copyright"] == "© 2024 Test Records"
        assert extracted["track_count"] == 12
        assert extracted["collection_view_url"] == "https://music.apple.com/album"
        assert extracted["collection_price"] == 9.99
        assert extracted["currency"] == "USD"

    def test_extract_album_with_defaults(self):
        """Test extraction with missing optional fields"""
        result = {"collectionId": 67890}

        extracted = extract_album_fields(result)

        assert extracted["collection_id"] == "67890"
        assert extracted["collection_name"] == ""
        assert extracted["primary_genre"] == "Unknown"
        assert extracted["track_count"] == 0


class TestExtractTrackFields:
    """Tests for extract_track_fields function"""

    def test_extract_complete_track_data(self):
        """Test extraction with all track fields"""
        result = {
            "artistId": 12345,
            "collectionId": 67890,
            "trackId": 111,
            "trackNumber": 1,
            "trackName": "Test Song",
            "trackTimeMillis": 180000,
            "previewUrl": "https://example.com/preview.m4a",
            "isPlayable": True,
            "explicit": False,
            "primaryGenreName": "Rock",
            "releaseDate": "2024-01-01",
            "collectionName": "Test Album",
            "artworkUrl600": "https://example.com/art600.jpg",
        }

        extracted = extract_track_fields(result)

        assert extracted["artist_id"] == "12345"
        assert extracted["collection_id"] == "67890"
        assert extracted["track_id"] == "111"
        assert extracted["track_number"] == 1
        assert extracted["track_name"] == "Test Song"
        assert extracted["track_duration_ms"] == 180000
        assert extracted["preview_url"] == "https://example.com/preview.m4a"
        assert extracted["is_playable"] is True
        assert extracted["explicit"] is False
        assert extracted["primary_genre"] == "Rock"
        assert extracted["release_date"] == "2024-01-01"
        assert extracted["collection_name"] == "Test Album"
        assert extracted["artwork_url_600"] == "https://example.com/art600.jpg"

    def test_extract_track_with_artwork_fallback(self):
        """Test artwork URL fallback logic"""
        result = {
            "trackId": 111,
            "artworkUrl100": "https://example.com/art100.jpg",
        }

        extracted = extract_track_fields(result)

        assert extracted["artwork_url_600"] == "https://example.com/art100.jpg"

    def test_extract_track_with_no_artwork(self):
        """Test extraction when no artwork is available"""
        result = {"trackId": 111}

        extracted = extract_track_fields(result)

        assert extracted["artwork_url_600"] == ""

    def test_extract_track_with_defaults(self):
        """Test extraction with missing optional fields"""
        result = {"trackId": 111}

        extracted = extract_track_fields(result)

        assert extracted["track_id"] == "111"
        assert extracted["track_name"] == ""
        assert extracted["track_number"] == 0
        assert extracted["track_duration_ms"] == 0
        assert extracted["preview_url"] == ""
        assert extracted["is_playable"] is True
        assert extracted["explicit"] is False
        assert extracted["primary_genre"] == "Unknown"
