# app/database.py
from sqlmodel import SQLModel, create_engine, Session

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
