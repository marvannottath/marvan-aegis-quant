"""
AEGIS-QUANT Unified Database Engine.
Manages transactional SQLite / PostgreSQL connection, session lifecycle,
auto-initialization, and data migration.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "aegis_quant.db"
DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create tables and initialize default data if needed."""
    Base.metadata.create_all(bind=engine)
    print(f"[DB ENGINE] Transactional Database initialized at: {DB_PATH}")


def get_db() -> Session:
    """Dependency / context manager generator for DB sessions."""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


# Auto-initialize database tables on module import
init_db()
