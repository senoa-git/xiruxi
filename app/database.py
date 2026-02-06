# app/database.py
from sqlmodel import SQLModel, create_engine, Session, select
from .models import User

DATABASE_URL = "sqlite:///./bottle.db"
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},  # SQLite用
)

def init_db() -> None:
    SQLModel.metadata.create_all(engine)

def get_session() -> Session:
    return Session(engine)

def get_user_by_anon_id(anon_id: str) -> User | None:
    with Session(engine) as session:
        return session.exec(select(User).where(User.anon_id == anon_id)).first()