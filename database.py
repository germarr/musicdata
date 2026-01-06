from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, create_engine, Session, select, Relationship
import uuid

DATABASE_URL = "sqlite:///./yolo_seg.db"
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    echo=False
)


class UserSession(SQLModel, table=True):
    """User session table"""
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    searches: list["Search"] = Relationship(back_populates="session")


class Search(SQLModel, table=True):
    """Search query table"""
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="usersession.session_id", index=True)
    artist_query: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    session: Optional[UserSession] = Relationship(back_populates="searches")
    results: list["Result"] = Relationship(back_populates="search")


class Result(SQLModel, table=True):
    """iTunes API result table"""
    id: Optional[int] = Field(default=None, primary_key=True)
    search_id: int = Field(foreign_key="search.id", index=True)
    artist_id: str
    artist_name: str = Field(index=True)
    primary_genre: str
    primary_genre_id: int
    artwork_url_100: Optional[str] = None
    artwork_url_60: Optional[str] = None
    artist_link_url: Optional[str] = None
    artist_type: str
    wrapper_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    search: Optional[Search] = Relationship(back_populates="results")


class ArtistCache(SQLModel, table=True):
    """Tracks which artists have had their albums/tracks fetched"""
    id: Optional[int] = Field(default=None, primary_key=True)
    artist_id: str = Field(index=True, unique=True)
    artist_name: str
    albums_collected: bool = Field(default=False)
    tracks_collected: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Track(SQLModel, table=True):
    """iTunes track/song metadata"""
    id: Optional[int] = Field(default=None, primary_key=True)
    artist_id: str = Field(index=True)
    collection_id: str = Field(index=True)
    track_id: str = Field(index=True)
    track_number: int
    track_name: str
    track_duration_ms: int
    preview_url: Optional[str] = None
    is_playable: bool = Field(default=True)
    explicit: bool = Field(default=False)
    primary_genre: str
    release_date: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


def create_db_and_tables():
    """Create database and tables"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get database session"""
    with Session(engine) as session:
        yield session


def get_or_create_session(db_session: Session, session_id: Optional[str] = None) -> UserSession:
    """Get existing session or create a new one"""
    if session_id:
        statement = select(UserSession).where(UserSession.session_id == session_id)
        user_session = db_session.exec(statement).first()
        if user_session:
            user_session.updated_at = datetime.utcnow()
            db_session.add(user_session)
            db_session.commit()
            db_session.refresh(user_session)
            return user_session
    
    # Create new session
    new_session_id = str(uuid.uuid4())
    user_session = UserSession(session_id=new_session_id)
    db_session.add(user_session)
    db_session.commit()
    db_session.refresh(user_session)
    return user_session


def get_or_create_artist_cache(db_session: Session, artist_id: str, artist_name: str) -> ArtistCache:
    """Get or create artist cache entry"""
    statement = select(ArtistCache).where(ArtistCache.artist_id == artist_id)
    cache = db_session.exec(statement).first()
    
    if cache:
        cache.updated_at = datetime.utcnow()
        db_session.add(cache)
        db_session.commit()
        db_session.refresh(cache)
        return cache
    
    # Create new cache entry
    cache = ArtistCache(artist_id=artist_id, artist_name=artist_name)
    db_session.add(cache)
    db_session.commit()
    db_session.refresh(cache)
    return cache


def is_artist_cached(db_session: Session, artist_id: str) -> bool:
    """Check if artist tracks have been cached"""
    statement = select(ArtistCache).where(
        ArtistCache.artist_id == artist_id,
        ArtistCache.tracks_collected == True
    )
    return db_session.exec(statement).first() is not None


def get_cached_artists(db_session: Session) -> list[ArtistCache]:
    """Get all artists with collected data"""
    statement = select(ArtistCache).where(ArtistCache.tracks_collected == True).order_by(ArtistCache.updated_at.desc())
    return db_session.exec(statement).all()


def get_artist_tracks(db_session: Session, artist_id: str, collection_id: str) -> list[Track]:
    """Get tracks for an artist/album"""
    statement = select(Track).where(
        Track.artist_id == artist_id,
        Track.collection_id == collection_id
    ).order_by(Track.track_number)
    return db_session.exec(statement).all()
