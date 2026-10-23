from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from backend.app.config import settings

DATABASE_URL = settings.database_url

# check_same_thread is a SQLite-only option and breaks other drivers.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_legacy_schema():
    """Add columns introduced after the initial SQLite schema was created."""
    if engine.dialect.name != "sqlite":
        return

    columns = {
        column["name"]
        for column in inspect(engine).get_columns("users")
    }

    if "is_active" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE users "
                    "ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
                )
            )