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
