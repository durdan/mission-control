"""
Base database models for Mission Control.
IMPORTANT: We store metadata and references only.
OpenClaw owns actual runtime state.
"""

from sqlalchemy import Column, DateTime, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncGenerator

Base = declarative_base()


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), nullable=False)


class OpenClawReferenceMixin:
    """
    Mixin for OpenClaw references.
    Mission Control stores references, OpenClaw owns the actual objects.
    """
    openclaw_agent_ref = Column(String, nullable=True, doc="Reference to OpenClaw agent ID")
    openclaw_session_ref = Column(String, nullable=True, doc="Reference to OpenClaw session")
    workspace_path = Column(String, nullable=True, doc="OpenClaw workspace path (read-only reference)")


# Database session management
async def get_async_session(database_url: str) -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    engine = create_async_engine(database_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session