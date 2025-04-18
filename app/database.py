# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession # Use async components

# from app.core.config import settings

# # Use async engine for FastAPI compatibility
# # check_same_thread=False is needed only for SQLite synchronous usage in multiple threads
# # For async SQLite (aiosqlite), it's handled differently.
# engine = create_async_engine(
#     settings.DATABASE_URL,
#     # echo=True # Set to True to see SQL queries (useful for debugging)
# )

# # Use AsyncSession for database operations within FastAPI/Celery async tasks
# AsyncSessionLocal = sessionmaker(
#     autocommit=False,
#     autoflush=False,
#     bind=engine,
#     class_=AsyncSession # Use AsyncSession class
# )

# Base = declarative_base()

# # Dependency to get DB session in FastAPI routes
# async def get_db() -> AsyncSession:
#     """FastAPI dependency that provides an async database session."""
#     async with AsyncSessionLocal() as session:
#         try:
#             yield session
#             await session.commit() # Commit if operations succeed (can be handled per-route too)
#         except Exception:
#             await session.rollback()
#             raise
#         finally:
#             await session.close() # Not strictly needed with context manager, but good practice



from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession # Use async components

from app.core.config import settings



from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base

from app.core.config import settings

# --- Keep Async Engine & Session for FastAPI ---
async_engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=async_engine, class_=AsyncSession
)

# --- Add Sync Engine & Session for Celery Tasks ---
# Create a standard synchronous engine using the same URL
# Need to ensure the sync driver is installed if not using sqlite
# (e.g., pip install psycopg2-binary for postgres, mysql-connector-python for mysql)
# For SQLite, the built-in driver works. Remove +aiosqlite part for sync.
sync_db_url = settings.DATABASE_URL.replace("+aiosqlite", "")
sync_engine = create_engine(
    sync_db_url,
    # Add pool settings if needed for non-SQLite DBs
    # pool_pre_ping=True, # Example
    # connect_args={"check_same_thread": False} # REQUIRED FOR SQLITE SYNC IN THREADS
)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# --- Base remains the same ---
Base = declarative_base()

# --- Keep Async get_db dependency ---
from typing import AsyncGenerator

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# --- Add Sync get_db_sync for potential sync routes/dependencies (Optional) ---
def get_db_sync():
    db = SyncSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()