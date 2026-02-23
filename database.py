import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Optionally load environment variables from a .env file (development convenience)
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    # dotenv is optional; requirements include python-dotenv so this should usually succeed
    pass

# Read database URL from environment; default to a local sqlite file for easy testing
# Example PostgreSQL URL: postgresql+psycopg2://user:password@localhost:5432/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# For sqlite we need connect_args, for others (e.g. postgresql+psycopg2) no special args
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency - yield a SQLAlchemy session and close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables. Call at application startup or manually."""
    Base.metadata.create_all(bind=engine)
