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
    collection_name: Optional[str] = None
    artwork_url_600: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GameSession(SQLModel, table=True):
    """Game session for bracket tournament"""
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: str = Field(index=True, unique=True)
    user_session_id: str = Field(foreign_key="usersession.session_id", index=True)
    artist_id: str = Field(index=True)
    status: str = Field(default="active")  # active, completed
    winner_track_id: Optional[str] = None
    winner_track_name: Optional[str] = None
    winner_artwork_url: Optional[str] = None
    total_rounds: int = Field(default=3)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    matches: list["GameMatch"] = Relationship(back_populates="game_session")


class GameMatch(SQLModel, table=True):
    """Individual match in the bracket"""
    id: Optional[int] = Field(default=None, primary_key=True)
    game_session_id: str = Field(foreign_key="gamesession.game_id", index=True)
    round_number: int = Field(index=True)
    match_number: int
    track_id_1: str
    track_name_1: str
    artwork_url_1: str
    track_id_2: str
    track_name_2: str
    artwork_url_2: str
    winner_track_id: Optional[str] = None
    loser_track_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    game_session: Optional[GameSession] = Relationship(back_populates="matches")


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


def get_all_artist_tracks(db_session: Session, artist_id: str) -> list[Track]:
    """Get all tracks for an artist (across all albums)"""
    statement = select(Track).where(Track.artist_id == artist_id).order_by(Track.track_number)
    return db_session.exec(statement).all()


def create_game_session(db_session: Session, user_session_id: str, artist_id: str) -> GameSession:
    """Create a new game session"""
    game_session = GameSession(
        game_id=str(uuid.uuid4()),
        user_session_id=user_session_id,
        artist_id=artist_id,
    )
    db_session.add(game_session)
    db_session.commit()
    db_session.refresh(game_session)
    return game_session


def get_game_session(db_session: Session, game_id: str) -> Optional[GameSession]:
    """Get a game session by ID"""
    statement = select(GameSession).where(GameSession.game_id == game_id)
    return db_session.exec(statement).first()


def create_game_match(
    db_session: Session,
    game_id: str,
    round_number: int,
    match_number: int,
    track_1: Track,
    track_2: Track,
) -> GameMatch:
    """Create a match in the bracket"""
    match = GameMatch(
        game_session_id=game_id,
        round_number=round_number,
        match_number=match_number,
        track_id_1=track_1.track_id,
        track_name_1=track_1.track_name,
        artwork_url_1=track_1.artwork_url_600 or "",
        track_id_2=track_2.track_id,
        track_name_2=track_2.track_name,
        artwork_url_2=track_2.artwork_url_600 or "",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)
    return match


def record_match_winner(
    db_session: Session,
    game_id: str,
    match_id: int,
    winner_track_id: str,
) -> Optional[GameMatch]:
    """Record the winner of a match"""
    statement = select(GameMatch).where(GameMatch.id == match_id)
    match = db_session.exec(statement).first()
    
    if match:
        match.winner_track_id = winner_track_id
        # Determine loser
        match.loser_track_id = (
            match.track_id_2 if winner_track_id == match.track_id_1
            else match.track_id_1
        )
        db_session.add(match)
        db_session.commit()
        db_session.refresh(match)
    
    return match


def get_game_matches(db_session: Session, game_id: str, round_number: int) -> list[GameMatch]:
    """Get all matches for a specific round"""
    statement = (
        select(GameMatch)
        .where(
            GameMatch.game_session_id == game_id,
            GameMatch.round_number == round_number,
        )
        .order_by(GameMatch.match_number)
    )
    return db_session.exec(statement).all()


def get_all_game_matches(db_session: Session, game_id: str) -> list[GameMatch]:
    """Get all matches for a game"""
    statement = (
        select(GameMatch)
        .where(GameMatch.game_session_id == game_id)
        .order_by(GameMatch.round_number, GameMatch.match_number)
    )
    return db_session.exec(statement).all()


def finish_game_session(
    db_session: Session,
    game_id: str,
    winner_track_id: str,
) -> Optional[GameSession]:
    """Mark game as completed and set winner"""
    statement = select(GameSession).where(GameSession.game_id == game_id)
    game = db_session.exec(statement).first()
    
    if game:
        # Get winner track info
        statement = select(Track).where(Track.track_id == winner_track_id)
        winner_track = db_session.exec(statement).first()
        
        if winner_track:
            game.winner_track_id = winner_track.track_id
            game.winner_track_name = winner_track.track_name
            game.winner_artwork_url = winner_track.artwork_url_600
        
        game.status = "completed"
        game.updated_at = datetime.utcnow()
        db_session.add(game)
        db_session.commit()
        db_session.refresh(game)
    
    return game
