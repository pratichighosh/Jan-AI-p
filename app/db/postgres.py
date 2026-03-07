from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, Text
import os
import structlog
from datetime import datetime
from typing import Optional, List, Dict

log = structlog.get_logger()

Base = declarative_base()
engine = None
SessionLocal = None


# ============================================================================
# Database Models
# ============================================================================

class Scheme(Base):
    __tablename__ = "schemes"
    
    id = Column(Integer, primary_key=True, index=True)
    scheme_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    name_hi = Column(String(255))
    description = Column(Text)
    required_fields = Column(JSON, default=list)
    required_documents = Column(JSON, default=list)
    field_guidance = Column(JSON, default=dict)  # Help text for each field
    keywords = Column(JSON, default=list)  # For classification
    form_numbers = Column(JSON, default=list)  # Official form numbers
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FieldGuidance(Base):
    __tablename__ = "field_guidance"
    
    id = Column(Integer, primary_key=True, index=True)
    scheme_id = Column(String(100), index=True, nullable=False)
    field_name = Column(String(100), nullable=False)
    title = Column(String(255))
    title_hi = Column(String(255))
    description = Column(Text)
    description_hi = Column(Text)
    example = Column(String(255))
    validation_rules = Column(JSON, default=dict)
    common_mistakes = Column(JSON, default=list)
    is_required = Column(Boolean, default=False)


# ============================================================================
# Database Connection
# ============================================================================

async def connect_to_postgres():
    """Initialize PostgreSQL connection on app startup."""
    global engine, SessionLocal
    
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://cais_user:cais_password@localhost:5432/cais_db"
    )
    
    try:
        engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
        
        SessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        log.info("postgres.connected", url=database_url.split('@')[-1])
    except Exception as e:
        log.exception("postgres.connection_failed", error=str(e))
        raise


async def close_postgres_connection():
    """Close PostgreSQL connection on app shutdown."""
    global engine
    if engine:
        await engine.dispose()
        log.info("postgres.disconnected")


# ============================================================================
# Scheme Operations
# ============================================================================

async def get_scheme_by_id(scheme_id: str) -> Optional[Dict]:
    """Get scheme details by ID."""
    async with SessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Scheme).where(Scheme.scheme_id == scheme_id)
        )
        scheme = result.scalar_one_or_none()
        
        if scheme:
            return {
                "scheme_id": scheme.scheme_id,
                "name": scheme.name,
                "name_hi": scheme.name_hi,
                "description": scheme.description,
                "required_fields": scheme.required_fields,
                "required_documents": scheme.required_documents,
                "field_guidance": scheme.field_guidance,
                "keywords": scheme.keywords,
                "form_numbers": scheme.form_numbers
            }
        return None


async def list_all_schemes() -> List[Dict]:
    """List all active schemes."""
    async with SessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(Scheme).where(Scheme.is_active == True)
        )
        schemes = result.scalars().all()
        
        return [
            {
                "scheme_id": s.scheme_id,
                "name": s.name,
                "name_hi": s.name_hi,
                "description": s.description
            }
            for s in schemes
        ]


async def create_scheme(scheme_data: Dict) -> str:
    """Create new scheme."""
    async with SessionLocal() as session:
        scheme = Scheme(**scheme_data)
        session.add(scheme)
        await session.commit()
        await session.refresh(scheme)
        
        log.info("postgres.scheme_created", scheme_id=scheme.scheme_id)
        return scheme.scheme_id


async def update_scheme(scheme_id: str, scheme_data: Dict) -> bool:
    """Update existing scheme."""
    async with SessionLocal() as session:
        from sqlalchemy import select, update
        
        stmt = (
            update(Scheme)
            .where(Scheme.scheme_id == scheme_id)
            .values(**scheme_data, updated_at=datetime.utcnow())
        )
        result = await session.execute(stmt)
        await session.commit()
        
        return result.rowcount > 0


# ============================================================================
# Field Guidance Operations
# ============================================================================

async def get_field_guidance(scheme_id: str, field_name: str) -> Optional[Dict]:
    """Get guidance for a specific field."""
    async with SessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(FieldGuidance).where(
                FieldGuidance.scheme_id == scheme_id,
                FieldGuidance.field_name == field_name
            )
        )
        guidance = result.scalar_one_or_none()
        
        if guidance:
            return {
                "field_name": guidance.field_name,
                "title": guidance.title,
                "title_hi": guidance.title_hi,
                "description": guidance.description,
                "description_hi": guidance.description_hi,
                "example": guidance.example,
                "validation_rules": guidance.validation_rules,
                "common_mistakes": guidance.common_mistakes,
                "is_required": guidance.is_required
            }
        return None


async def list_field_guidance(scheme_id: str) -> List[Dict]:
    """List all field guidance for a scheme."""
    async with SessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(FieldGuidance).where(FieldGuidance.scheme_id == scheme_id)
        )
        guidance_list = result.scalars().all()
        
        return [
            {
                "field_name": g.field_name,
                "title": g.title,
                "title_hi": g.title_hi,
                "is_required": g.is_required
            }
            for g in guidance_list
        ]