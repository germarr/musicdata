from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
import uuid
import os
import asyncio

from database import (
    create_db_and_tables,
    get_session,
    get_or_create_session,
    UserSession,
    Search,
    Result,
    ArtistCache,
    Track,
    GameSession,
    GameMatch,
    engine,
    is_artist_cached,
    get_cached_artists,
    get_artist_tracks,
    get_or_create_artist_cache,
    get_all_artist_tracks,
    create_game_session,
    get_game_session,
    create_game_match,
    record_match_winner,
    get_game_matches,
    get_all_game_matches,
    finish_game_session,
)
from itunes_client import (
    search_artists,
    extract_artist_fields,
    search_albums_by_artist,
    extract_album_fields,
    get_album_tracks,
    extract_track_fields,
)

# Initialize app
app = FastAPI(title="iTunes Artist Search")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Create database tables
create_db_and_tables()

# Session cookie configuration
SESSION_COOKIE_NAME = "session_id"
SESSION_COOKIE_DAYS = 30


class SearchRequest(BaseModel):
    artist_name: str


class ArtistResult(BaseModel):
    artist_id: str
    artist_name: str
    primary_genre: str
    artwork_url_100: str
    artist_link_url: str
    artist_type: str


class SearchResponse(BaseModel):
    results: list[ArtistResult]


class AlbumResult(BaseModel):
    collection_id: str
    collection_name: str
    artist_name: str
    artwork_url_100: str = ""
    artwork_url_600: str = ""
    primary_genre: str = "Unknown"
    release_date: str = ""
    track_count: int = 0
    collection_view_url: str = ""
    collection_price: float = 0.0
    currency: str = "USD"


class AlbumsResponse(BaseModel):
    artist_id: str
    artist_name: str
    albums: list[AlbumResult]


class TrackResult(BaseModel):
    track_id: str
    track_number: int
    track_name: str
    track_duration_ms: int
    preview_url: str = ""
    explicit: bool = False
    primary_genre: str = "Unknown"


class AlbumTracksResponse(BaseModel):
    collection_id: str
    collection_name: str
    artist_name: str
    artist_id: str
    tracks: list[TrackResult]
    total_tracks: int


class CachedArtist(BaseModel):
    artist_id: str
    artist_name: str
    tracks_collected: bool
    updated_at: datetime
    artwork_url: Optional[str] = None


class CachedArtistsResponse(BaseModel):
    artists: list[CachedArtist]


class GameTrack(BaseModel):
    track_id: str
    track_name: str
    artwork_url_600: str
    preview_url: Optional[str] = None


class GameMatchResponse(BaseModel):
    match_id: int
    round_number: int
    match_number: int
    track_1: GameTrack
    track_2: GameTrack


class GameStartResponse(BaseModel):
    game_id: str
    artist_id: str
    matches: list[GameMatchResponse]
    round_number: int = 1


class GameMatchResultRequest(BaseModel):
    game_id: str
    match_id: int
    winner_track_id: str


class GameResultsResponse(BaseModel):
    game_id: str
    status: str
    winner_track_id: str
    winner_track_name: str
    winner_artwork_url: str
    winner_preview_url: Optional[str] = None
    dismissed_tracks: list[GameTrack]
    created_at: datetime


def get_session_id(request: Request) -> str:
    """Extract session ID from cookie or request state"""
    # First check if it's in the request state (set by middleware)
    if hasattr(request.state, "session_id"):
        return request.state.session_id
    # Fall back to cookie
    return request.cookies.get(SESSION_COOKIE_NAME)


def get_user_session(
    request: Request,
    db: Session = Depends(get_session),
) -> UserSession:
    """Get or create user session"""
    session_id = get_session_id(request)
    return get_or_create_session(db, session_id)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/search", response_model=SearchResponse)
async def search(
    search_request: SearchRequest,
    request: Request,
    db: Session = Depends(get_session),
):
    """
    Search for artists on iTunes API
    Store query and results in database
    """
    # Get session ID from cookie (guaranteed to exist from middleware)
    session_id = get_session_id(request)
    
    # Call iTunes API
    results = await search_artists(search_request.artist_name.strip())
    
    # Create search record
    search_record = Search(
        session_id=session_id,
        artist_query=search_request.artist_name.strip(),
    )
    db.add(search_record)
    db.commit()
    db.refresh(search_record)
    
    # Store results in database
    artist_results = []
    for result in results:
        extracted = extract_artist_fields(result)
        db_result = Result(
            search_id=search_record.id,
            **extracted,
        )
        db.add(db_result)
        artist_results.append(
            ArtistResult(
                artist_id=extracted["artist_id"],
                artist_name=extracted["artist_name"],
                primary_genre=extracted["primary_genre"],
                artwork_url_100=extracted["artwork_url_100"],
                artist_link_url=extracted["artist_link_url"],
                artist_type=extracted["artist_type"],
            )
        )
    
    db.commit()
    
    return SearchResponse(results=artist_results)


@app.get("/history")
async def get_history(
    request: Request,
    db: Session = Depends(get_session),
):
    """Get search history for the current session"""
    session_id = get_session_id(request)
    
    if not session_id:
        return {"searches": []}
    
    statement = (
        select(Search)
        .where(Search.session_id == session_id)
        .order_by(Search.created_at.desc())
        .limit(20)
    )
    searches = db.exec(statement).all()
    
    return {
        "searches": [
            {
                "id": s.id,
                "artist_query": s.artist_query,
                "created_at": s.created_at.isoformat(),
            }
            for s in searches
        ]
    }


@app.get("/albums")
async def get_albums_page(request: Request):
    """Serve the albums page"""
    return templates.TemplateResponse("albums.html", {"request": request})


@app.get("/collected-artists")
async def get_collected_artists_page(request: Request):
    """Serve the collected artists page"""
    return templates.TemplateResponse("collected-artists.html", {"request": request})


@app.get("/collected-tracks")
async def get_collected_tracks_page(request: Request):
    """Serve the collected tracks page"""
    return templates.TemplateResponse("collected-tracks.html", {"request": request})


@app.get("/game")
async def get_game_page(request: Request):
    """Serve the game page"""
    return templates.TemplateResponse("game.html", {"request": request})


@app.get("/api/albums/{artist_id}")
async def get_artist_albums(artist_id: int) -> AlbumsResponse:
    """
    Get albums for a specific artist
    
    Args:
        artist_id: iTunes artist ID
    
    Returns:
        List of albums with all iTunes data
    """
    # Get albums from iTunes API
    albums = await search_albums_by_artist(artist_id, limit=50)
    
    if not albums:
        return AlbumsResponse(
            artist_id=str(artist_id),
            artist_name="Unknown",
            albums=[]
        )
    
    # Get artist name from first album
    artist_name = albums[0].get("artistName", "Unknown")
    
    # Extract album fields
    album_results = [
        AlbumResult(
            collection_id=str(album.get("collectionId", "")),
            collection_name=album.get("collectionName", ""),
            artist_name=album.get("artistName", ""),
            artwork_url_100=album.get("artworkUrl100", ""),
            artwork_url_600=album.get("artworkUrl600", album.get("artworkUrl100", "")),  # fallback to 100 if 600 not available
            primary_genre=album.get("primaryGenreName", "Unknown"),
            release_date=album.get("releaseDate", ""),
            track_count=album.get("trackCount", 0),
            collection_view_url=album.get("collectionViewUrl", ""),
            collection_price=float(album.get("collectionPrice", 0)),
            currency=album.get("currency", "USD"),
        )
        for album in albums
    ]
    
    return AlbumsResponse(
        artist_id=str(artist_id),
        artist_name=artist_name,
        albums=album_results
    )


@app.post("/api/collect-album-tracks/{artist_id}/{collection_id}")
async def collect_album_tracks(artist_id: str, collection_id: str, db: Session = Depends(get_session)):
    """
    Collect and store all tracks for an album
    Includes rate limiting (delay between API calls)
    
    Args:
        artist_id: iTunes artist ID
        collection_id: iTunes collection/album ID
    
    Returns:
        Album tracks with metadata
    """
    # Check if already cached
    if is_artist_cached(db, artist_id):
        # Return cached tracks
        tracks = get_artist_tracks(db, artist_id, collection_id)
        if tracks:
            return AlbumTracksResponse(
                collection_id=collection_id,
                collection_name=tracks[0].__dict__.get('track_name', 'Unknown') if tracks else "Unknown",
                artist_name="",
                artist_id=artist_id,
                tracks=[
                    TrackResult(
                        track_id=t.track_id,
                        track_number=t.track_number,
                        track_name=t.track_name,
                        track_duration_ms=t.track_duration_ms,
                        preview_url=t.preview_url or "",
                        explicit=t.explicit,
                        primary_genre=t.primary_genre,
                    )
                    for t in tracks
                ],
                total_tracks=len(tracks),
            )
    
    # Fetch from iTunes API with rate limiting
    try:
        tracks_data = await get_album_tracks(int(collection_id))
    except Exception as e:
        print(f"Error fetching tracks: {e}")
        return AlbumTracksResponse(
            collection_id=collection_id,
            collection_name="Unknown",
            artist_name="",
            artist_id=artist_id,
            tracks=[],
            total_tracks=0,
        )
    
    if not tracks_data:
        return AlbumTracksResponse(
            collection_id=collection_id,
            collection_name="Unknown",
            artist_name="",
            artist_id=artist_id,
            tracks=[],
            total_tracks=0,
        )
    
    # Extract artist name from track data
    artist_name = tracks_data[0].get("artistName", "") if tracks_data else ""
    
    # Get or create artist cache with artist name
    get_or_create_artist_cache(db, artist_id, artist_name)
    
    # Store tracks in database
    stored_tracks = []
    for track_data in tracks_data:
        extracted = extract_track_fields(track_data)
        # Remove artist_id and collection_id from extracted since we're providing them
        extracted.pop('artist_id', None)
        extracted.pop('collection_id', None)
        
        db_track = Track(
            artist_id=artist_id,
            collection_id=collection_id,
            **extracted,
        )
        db.add(db_track)
        stored_tracks.append(db_track)
        
        # Rate limiting: small delay between storing (0.05 seconds)
        await asyncio.sleep(0.05)
    
    db.commit()
    
    # Mark as collected
    statement = select(ArtistCache).where(ArtistCache.artist_id == artist_id)
    cache = db.exec(statement).first()
    if cache:
        cache.tracks_collected = True
        cache.updated_at = datetime.utcnow()
        db.add(cache)
        db.commit()
    
    # Get collection name from first track
    collection_name = tracks_data[0].get("collectionName", "Unknown") if tracks_data else "Unknown"
    
    return AlbumTracksResponse(
        collection_id=collection_id,
        collection_name=collection_name,
        artist_name=artist_name,
        artist_id=artist_id,
        tracks=[
            TrackResult(
                track_id=t.track_id,
                track_number=t.track_number,
                track_name=t.track_name,
                track_duration_ms=t.track_duration_ms,
                preview_url=t.preview_url or "",
                explicit=t.explicit,
                primary_genre=t.primary_genre,
            )
            for t in stored_tracks
        ],
        total_tracks=len(stored_tracks),
    )


@app.post("/api/collect-all-artist-tracks/{artist_id}")
async def collect_all_artist_tracks(artist_id: str, db: Session = Depends(get_session)):
    """
    Collect tracks from ALL albums for an artist
    Skips tracks already in database (by track_id)
    Returns progress information and summary
    """
    try:
        # Fetch all albums for this artist
        albums = await search_albums_by_artist(int(artist_id), limit=150)
        
        if not albums:
            return {
                "artist_id": artist_id,
                "total_albums": 0,
                "total_tracks_collected": 0,
                "albums": [],
            }
        
        # Get artist name from first album
        artist_name = albums[0].get("artistName", "")
        
        # Get or create artist cache
        get_or_create_artist_cache(db, artist_id, artist_name)
        
        # Filter to only album collections
        album_collections = [
            a for a in albums 
            if a.get("wrapperType") == "collection" and a.get("collectionType") == "Album"
        ]
        
        # Collect tracks from all albums
        collected_albums = []
        total_tracks_new = 0
        
        for idx, album in enumerate(album_collections):
            collection_id = album.get("collectionId")
            
            try:
                # Fetch tracks for this album
                tracks_data = await get_album_tracks(collection_id)
                
                if not tracks_data:
                    collected_albums.append({
                        "collection_id": str(collection_id),
                        "collection_name": album.get("collectionName", ""),
                        "new_tracks": 0,
                        "skipped_tracks": 0,
                    })
                    continue
                
                new_tracks_count = 0
                skipped_tracks_count = 0
                
                # Process each track
                for track_data in tracks_data:
                    track_id = str(track_data.get("trackId", ""))
                    
                    # Check if track already exists
                    existing = db.exec(
                        select(Track).where(Track.track_id == track_id)
                    ).first()
                    
                    if existing:
                        skipped_tracks_count += 1
                        continue
                    
                    # Extract and store new track
                    extracted = extract_track_fields(track_data)
                    extracted.pop('artist_id', None)
                    extracted.pop('collection_id', None)
                    
                    db_track = Track(
                        artist_id=artist_id,
                        collection_id=str(collection_id),
                        **extracted,
                    )
                    db.add(db_track)
                    new_tracks_count += 1
                    total_tracks_new += 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.05)
                
                db.commit()
                
                collected_albums.append({
                    "collection_id": str(collection_id),
                    "collection_name": album.get("collectionName", ""),
                    "new_tracks": new_tracks_count,
                    "skipped_tracks": skipped_tracks_count,
                })
                
            except Exception as e:
                print(f"Error collecting tracks from album {collection_id}: {e}")
                continue
        
        # Mark artist as fully collected
        statement = select(ArtistCache).where(ArtistCache.artist_id == artist_id)
        cache = db.exec(statement).first()
        if cache:
            cache.tracks_collected = True
            cache.updated_at = datetime.utcnow()
            db.add(cache)
            db.commit()
        
        return {
            "artist_id": artist_id,
            "artist_name": artist_name,
            "total_albums": len(album_collections),
            "total_tracks_collected": total_tracks_new,
            "albums": collected_albums,
        }
        
    except Exception as e:
        print(f"Error in collect_all_artist_tracks: {e}")
        return {
            "artist_id": artist_id,
            "error": str(e),
            "total_albums": 0,
            "total_tracks_collected": 0,
            "albums": [],
        }


@app.get("/api/cached-artists")
async def get_all_cached_artists(db: Session = Depends(get_session)) -> CachedArtistsResponse:
    """Get all artists with collected track data and artwork"""
    cached = get_cached_artists(db)
    
    artists_list = []
    for artist in cached:
        # Get first track's artwork for this artist
        artwork_url = None
        first_track = db.exec(
            select(Track.artwork_url_600).where(Track.artist_id == artist.artist_id).limit(1)
        ).first()
        if first_track:
            artwork_url = first_track
        
        artists_list.append(
            CachedArtist(
                artist_id=artist.artist_id,
                artist_name=artist.artist_name,
                tracks_collected=artist.tracks_collected,
                updated_at=artist.updated_at,
                artwork_url=artwork_url,
            )
        )
    
    return CachedArtistsResponse(artists=artists_list)


@app.get("/api/artists-with-track-counts")
async def get_artists_with_track_counts(db: Session = Depends(get_session)):
    """Get all artists with their collected track counts and albums with global metrics"""
    cached = get_cached_artists(db)
    
    artists_data = []
    total_duration_ms = 0
    total_albums_set = set()
    
    for artist in cached:
        # Get all albums for this artist
        albums = db.exec(
            select(Track.collection_id).where(Track.artist_id == artist.artist_id).distinct()
        ).all()
        
        # Get track count for this artist
        track_count = db.exec(
            select(func.count(Track.id)).where(Track.artist_id == artist.artist_id)
        ).first()
        
        # Get duration for this artist
        tracks_for_artist = db.exec(
            select(Track).where(Track.artist_id == artist.artist_id)
        ).all()
        
        for track in tracks_for_artist:
            total_duration_ms += track.track_duration_ms
            total_albums_set.add(track.collection_id)
        
        artists_data.append({
            "artist_id": artist.artist_id,
            "artist_name": artist.artist_name,
            "album_count": len(set(albums)) if albums else 0,
            "track_count": track_count or 0,
            "updated_at": artist.updated_at.isoformat(),
        })
    
    total_tracks = sum(a["track_count"] for a in artists_data)
    avg_duration_ms = int(total_duration_ms / total_tracks) if total_tracks > 0 else 0
    
    return {
        "artists": artists_data,
        "total_artists": len(artists_data),
        "total_tracks": total_tracks,
        "total_albums": len(total_albums_set),
        "avg_duration_ms": avg_duration_ms,
    }


@app.get("/api/tracks/{artist_id}")
async def get_artist_all_tracks(artist_id: str, db: Session = Depends(get_session)):
    """Get all tracks for an artist grouped by album with artist-specific metrics"""
    statement = select(Track).where(Track.artist_id == artist_id).order_by(
        Track.collection_id, Track.track_number
    )
    tracks = db.exec(statement).all()
    
    if not tracks:
        return {
            "artist_id": artist_id,
            "albums": [],
            "total_tracks": 0,
            "total_albums": 0,
            "avg_duration_ms": 0,
        }
    
    # Group tracks by album
    albums_dict = {}
    total_duration_ms = 0
    
    for track in tracks:
        total_duration_ms += track.track_duration_ms
        if track.collection_id not in albums_dict:
            albums_dict[track.collection_id] = {
                "collection_id": track.collection_id,
                "collection_name": track.collection_name or f"Album {track.collection_id}",
                "artwork_url_600": track.artwork_url_600 or "",
                "tracks": []
            }
        albums_dict[track.collection_id]["tracks"].append({
            "track_id": track.track_id,
            "track_number": track.track_number,
            "track_name": track.track_name,
            "track_duration_ms": track.track_duration_ms,
            "preview_url": track.preview_url or "",
            "explicit": track.explicit,
            "primary_genre": track.primary_genre,
            "release_date": track.release_date or "",
        })
    
    # Calculate average duration
    avg_duration_ms = int(total_duration_ms / len(tracks)) if tracks else 0
    
    return {
        "artist_id": artist_id,
        "albums": list(albums_dict.values()),
        "total_tracks": len(tracks),
        "total_albums": len(albums_dict),
        "avg_duration_ms": avg_duration_ms,
    }


@app.post("/api/game/start/{artist_id}")
async def start_game(
    artist_id: str,
    request: Request,
    db: Session = Depends(get_session),
):
    """
    Start a new bracket game for an artist
    Retrieves all collected tracks and creates the initial bracket (Round 1 with 8 matches)
    """
    session_id = get_session_id(request)
    
    # Get all tracks for the artist
    all_tracks = get_all_artist_tracks(db, artist_id)
    
    if len(all_tracks) < 2:
        return {
            "error": "Need at least 2 tracks to start a game",
            "available_tracks": len(all_tracks),
        }
    
    # Create game session
    game = create_game_session(db, session_id, artist_id)
    
    # Shuffle tracks and take up to 8 for the first round
    import random
    shuffled_tracks = random.sample(all_tracks, min(len(all_tracks), 8))
    
    # Create initial matches (Round 1)
    matches = []
    for i in range(0, len(shuffled_tracks), 2):
        track_1 = shuffled_tracks[i]
        track_2 = shuffled_tracks[i + 1] if i + 1 < len(shuffled_tracks) else shuffled_tracks[0]
        
        match = create_game_match(
            db,
            game.game_id,
            round_number=1,
            match_number=len(matches) + 1,
            track_1=track_1,
            track_2=track_2,
        )
        
        matches.append(
            GameMatchResponse(
                match_id=match.id,
                round_number=match.round_number,
                match_number=match.match_number,
                track_1=GameTrack(
                    track_id=match.track_id_1,
                    track_name=match.track_name_1,
                    artwork_url_600=match.artwork_url_1,
                    preview_url=track_1.preview_url,
                ),
                track_2=GameTrack(
                    track_id=match.track_id_2,
                    track_name=match.track_name_2,
                    artwork_url_600=match.artwork_url_2,
                    preview_url=track_2.preview_url,
                ),
            )
        )
    
    return GameStartResponse(
        game_id=game.game_id,
        artist_id=artist_id,
        matches=matches,
        round_number=1,
    )


@app.post("/api/game/match-result")
async def record_match(
    result: GameMatchResultRequest,
    db: Session = Depends(get_session),
):
    """
    Record the result of a match and determine next matches
    If all matches in a round are complete, generates next round
    """
    # Record the winner
    match = record_match_winner(db, result.game_id, result.match_id, result.winner_track_id)
    
    if not match:
        return {"error": "Match not found"}
    
    # Get the game
    game = get_game_session(db, result.game_id)
    if not game:
        return {"error": "Game not found"}
    
    # Get all matches for current round
    round_matches = get_game_matches(db, result.game_id, match.round_number)
    
    # Check if all matches in this round are complete
    all_complete = all(m.winner_track_id for m in round_matches)
    
    if not all_complete:
        return {
            "game_id": result.game_id,
            "status": "round_in_progress",
            "current_round": match.round_number,
        }
    
    # Determine if game is complete
    if len(round_matches) == 1:
        # This was the final match - game is complete
        finish_game_session(db, result.game_id, result.winner_track_id)
        return {
            "game_id": result.game_id,
            "status": "completed",
            "winner_track_id": result.winner_track_id,
        }
    
    # Create next round matches
    next_round_number = match.round_number + 1
    winners = [m.winner_track_id for m in round_matches]
    
    # Get winner track details
    statement = select(Track).where(Track.track_id.in_(winners))
    winner_tracks_dict = {t.track_id: t for t in db.exec(statement).all()}
    winner_tracks = [winner_tracks_dict[wid] for wid in winners if wid in winner_tracks_dict]
    
    # Create matches for next round
    next_matches = []
    for i in range(0, len(winner_tracks), 2):
        track_1 = winner_tracks[i]
        track_2 = winner_tracks[i + 1] if i + 1 < len(winner_tracks) else winner_tracks[0]
        
        next_match = create_game_match(
            db,
            result.game_id,
            round_number=next_round_number,
            match_number=len(next_matches) + 1,
            track_1=track_1,
            track_2=track_2,
        )
        
        next_matches.append(
            GameMatchResponse(
                match_id=next_match.id,
                round_number=next_match.round_number,
                match_number=next_match.match_number,
                track_1=GameTrack(
                    track_id=next_match.track_id_1,
                    track_name=next_match.track_name_1,
                    artwork_url_600=next_match.artwork_url_1,
                    preview_url=track_1.preview_url,
                ),
                track_2=GameTrack(
                    track_id=next_match.track_id_2,
                    track_name=next_match.track_name_2,
                    artwork_url_600=next_match.artwork_url_2,
                    preview_url=track_2.preview_url,
                ),
            )
        )
    
    return {
        "game_id": result.game_id,
        "status": "next_round",
        "current_round": next_round_number,
        "matches": next_matches,
    }


@app.get("/api/game/results/{game_id}")
async def get_game_results(game_id: str, db: Session = Depends(get_session)):
    """
    Get the final results of a completed game
    Returns winner and all dismissed (losing) tracks
    """
    game = get_game_session(db, game_id)
    
    if not game:
        return {"error": "Game not found"}
    
    if game.status != "completed":
        return {"error": "Game is not completed"}
    
    # Get all matches
    all_matches = get_all_game_matches(db, game_id)
    
    # Collect all dismissed track IDs
    dismissed_ids = [m.loser_track_id for m in all_matches if m.loser_track_id]
    
    # Get dismissed track details
    dismissed_tracks = []
    if dismissed_ids:
        statement = select(Track).where(Track.track_id.in_(dismissed_ids))
        tracks = db.exec(statement).all()
        dismissed_tracks = [
            GameTrack(
                track_id=t.track_id,
                track_name=t.track_name,
                artwork_url_600=t.artwork_url_600 or "",
                preview_url=t.preview_url,
            )
            for t in tracks
        ]
    
    # Get winner preview URL
    winner_preview_url = None
    if game.winner_track_id:
        statement = select(Track).where(Track.track_id == game.winner_track_id)
        winner_track = db.exec(statement).first()
        if winner_track:
            winner_preview_url = winner_track.preview_url
    
    return GameResultsResponse(
        game_id=game.game_id,
        status=game.status,
        winner_track_id=game.winner_track_id or "",
        winner_track_name=game.winner_track_name or "",
        winner_artwork_url=game.winner_artwork_url or "",
        winner_preview_url=winner_preview_url,
        dismissed_tracks=dismissed_tracks,
        created_at=game.created_at,
    )



async def session_middleware(request: Request, call_next):
    """Middleware to handle session cookies and database sessions"""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    
    # If no session, create one in the database
    if not session_id:
        with Session(engine) as db:
            session_id = str(uuid.uuid4())
            user_session = UserSession(session_id=session_id)
            db.add(user_session)
            db.commit()
    
    # Store session_id in request state so route handlers can access it
    request.state.session_id = session_id
    
    response = await call_next(request)
    
    # Set session cookie
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=60 * 60 * 24 * SESSION_COOKIE_DAYS,
        httponly=True,
        samesite="lax",
    )
    
    return response


# Register session middleware
app.middleware("http")(session_middleware)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
