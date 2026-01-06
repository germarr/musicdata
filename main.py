from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from datetime import datetime, timedelta
from pydantic import BaseModel
import uuid
import os

from database import (
    create_db_and_tables,
    get_session,
    get_or_create_session,
    UserSession,
    Search,
    Result,
    engine,
)
from itunes_client import search_artists, extract_artist_fields, search_albums_by_artist, extract_album_fields

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


@app.middleware("http")
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
