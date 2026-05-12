import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

logger = logging.getLogger("laura.database")

DATABASE_URL = f"postgresql://{settings.db_user}:{settings.db_password}@{settings.db_host}:{settings.db_port}/{settings.db_name}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import app.models
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("database_tables_created", extra={"tables": list(Base.metadata.tables.keys())})
    except Exception as e:
        logger.exception("database_init_failed", extra={"error": str(e)})
        raise
