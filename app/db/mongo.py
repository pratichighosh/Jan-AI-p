import os
import structlog
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, List
from datetime import datetime

log = structlog.get_logger()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "cais_db")

_client: Optional[AsyncIOMotorClient] = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(MONGODB_URI)
    return _client


def get_db():
    return get_client()[MONGODB_DB_NAME]


def get_documents_collection():
    return get_db()["documents"]


def get_progress_collection():
    return get_db()["progress"]


async def save_document(document_data: Dict) -> str:
    """Save document processing result to MongoDB."""
    document_data["created_at"] = datetime.utcnow()
    document_data["updated_at"] = datetime.utcnow()
    col = get_documents_collection()
    result = await col.insert_one(document_data)
    log.info("mongodb.document_saved", document_id=document_data.get("document_id"))
    return str(result.inserted_id)


async def get_document(document_id: str) -> Optional[Dict]:
    """Retrieve document by document_id."""
    col = get_documents_collection()
    doc = await col.find_one({"document_id": document_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def update_document(document_id: str, update_data: Dict) -> bool:
    """Update document fields."""
    update_data["updated_at"] = datetime.utcnow()
    col = get_documents_collection()
    result = await col.update_one(
        {"document_id": document_id},
        {"$set": update_data},
    )
    return result.modified_count > 0


async def list_user_documents(
    user_id: str,
    limit: int = 50,
    skip: int = 0,
) -> List[Dict]:
    """List all documents for a user, newest first."""
    col = get_documents_collection()
    cursor = (
        col.find({"user_id": user_id})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    documents = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        documents.append(doc)
    return documents


async def save_progress(document_id: str, completed_actions: list) -> str:
    """Save or update progress for a document."""
    col = get_progress_collection()
    result = await col.update_one(
        {"document_id": document_id},
        {
            "$set": {
                "document_id": document_id,
                "completed_actions": completed_actions,
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )
    log.info("mongodb.progress_saved", document_id=document_id)
    return str(result.upserted_id) if result.upserted_id else "updated"


async def get_progress(document_id: str) -> Optional[Dict]:
    """Get progress for a document."""
    col = get_progress_collection()
    progress = await col.find_one({"document_id": document_id})
    if progress:
        progress["_id"] = str(progress["_id"])
    return progress
