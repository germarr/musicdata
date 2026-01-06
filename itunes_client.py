import httpx
from typing import List, Dict, Any

ITUNES_API_BASE = "https://itunes.apple.com"


async def search_artists(artist_name: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Search for artists on iTunes API
    
    Args:
        artist_name: Name of the artist to search for
        limit: Maximum number of results (default 50)
    
    Returns:
        List of unique artist results from iTunes API
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{ITUNES_API_BASE}/search",
                params={
                    "term": artist_name,
                    "limit": limit,
                }
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            
            # Extract unique artists from results
            seen_artists = {}
            artist_results = []
            
            for result in results:
                artist_id = result.get("artistId")
                artist_name_result = result.get("artistName", "")
                
                # Skip if no artist info
                if not artist_id or not artist_name_result:
                    continue
                
                # Only add each artist once
                if artist_id not in seen_artists:
                    seen_artists[artist_id] = True
                    artist_results.append(result)
            
            return artist_results
        except httpx.HTTPError as e:
            print(f"Error calling iTunes API: {e}")
            return []


async def search_albums_by_artist(artist_id: int, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Search for albums by artist ID
    
    Args:
        artist_id: iTunes artist ID
        limit: Maximum number of results (default 50)
    
    Returns:
        List of album results from iTunes API
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{ITUNES_API_BASE}/lookup",
                params={
                    "id": artist_id,
                    "entity": "album",
                    "limit": limit,
                }
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            
            # Filter to only albums (skip the artist result itself)
            albums = [r for r in results if r.get("wrapperType") == "collection" and r.get("collectionType") == "Album"]
            return albums
        except httpx.HTTPError as e:
            print(f"Error calling iTunes API: {e}")
            return []


def extract_artist_fields(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant fields from iTunes API result
    
    Args:
        result: Raw result from iTunes API
    
    Returns:
        Dictionary with extracted artist fields
    """
    # Use artistViewUrl as the main link, fall back to trackViewUrl
    artist_link = result.get("artistViewUrl", result.get("trackViewUrl", ""))
    
    return {
        "artist_id": str(result.get("artistId", "")),
        "artist_name": result.get("artistName", ""),
        "primary_genre": result.get("primaryGenreName", "Unknown"),
        "primary_genre_id": result.get("primaryGenreId", 0),
        "artwork_url_100": result.get("artworkUrl100", ""),
        "artwork_url_60": result.get("artworkUrl60", ""),
        "artist_link_url": artist_link,
        "artist_type": "Artist",  # All extracted are artists
        "wrapper_type": "artist",  # Normalized type
    }


def extract_album_fields(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant fields from iTunes API album result
    
    Args:
        result: Raw album result from iTunes API
    
    Returns:
        Dictionary with extracted album fields
    """
    return {
        "collection_id": str(result.get("collectionId", "")),
        "collection_name": result.get("collectionName", ""),
        "artist_name": result.get("artistName", ""),
        "artist_id": str(result.get("artistId", "")),
        "artwork_url_100": result.get("artworkUrl100", ""),
        "artwork_url_600": result.get("artworkUrl600", ""),
        "primary_genre": result.get("primaryGenreName", "Unknown"),
        "release_date": result.get("releaseDate", ""),
        "copyright": result.get("copyright", ""),
        "track_count": result.get("trackCount", 0),
        "collection_view_url": result.get("collectionViewUrl", ""),
        "collection_price": result.get("collectionPrice", 0),
        "currency": result.get("currency", ""),
    }


async def get_album_tracks(collection_id: int) -> List[Dict[str, Any]]:
    """
    Get all tracks for a specific album
    
    Args:
        collection_id: iTunes collection/album ID
    
    Returns:
        List of track results from iTunes API
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{ITUNES_API_BASE}/lookup",
                params={
                    "id": collection_id,
                    "entity": "song",
                    "limit": 200,
                }
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            
            # Filter to only tracks (skip the album result itself)
            tracks = [r for r in results if r.get("wrapperType") == "track" and r.get("kind") == "song"]
            return tracks
        except httpx.HTTPError as e:
            print(f"Error calling iTunes API: {e}")
            return []


def extract_track_fields(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant fields from iTunes API track result
    
    Args:
        result: Raw track result from iTunes API
    
    Returns:
        Dictionary with extracted track fields
    """
    # Convert duration from milliseconds
    duration_ms = result.get("trackTimeMillis", 0)
    
    return {
        "artist_id": str(result.get("artistId", "")),
        "collection_id": str(result.get("collectionId", "")),
        "track_id": str(result.get("trackId", "")),
        "track_number": result.get("trackNumber", 0),
        "track_name": result.get("trackName", ""),
        "track_duration_ms": duration_ms,
        "preview_url": result.get("previewUrl", ""),
        "is_playable": result.get("isPlayable", True),
        "explicit": result.get("explicit", False),
        "primary_genre": result.get("primaryGenreName", "Unknown"),
        "release_date": result.get("releaseDate", ""),
    }
