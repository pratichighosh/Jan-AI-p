from fastapi import APIRouter, HTTPException
from typing import List

from app.db.mongo import get_db
from app.core.scoring.readiness import calculate_readiness_score

router = APIRouter(tags=["progress"])


def _get_progress_collection():
    return get_db()["progress"]


def _get_documents_collection():
    return get_db()["documents"]


def _recalculate_score(
    ocr_text: str,
    scheme_id: str,
    completed_actions: List[str],
) -> dict:
    """
    Recalculate readiness score treating completed action fields/docs
    as if they are now present in the document.
    """
    # Extract which fields and docs have been completed
    completed_fields = [
        a.replace("field_", "")
        for a in completed_actions
        if a.startswith("field_")
    ]
    completed_docs = [
        a.replace("doc_", "")
        for a in completed_actions
        if a.startswith("doc_")
    ]

    # Pass completed docs as uploaded_docs so scorer counts them
    result = calculate_readiness_score(
        ocr_text=ocr_text,
        scheme_id=scheme_id,
        uploaded_docs=completed_docs,
        completed_action_fields=completed_fields,
    )
    return result


@router.get("/progress/{document_id}")
async def get_progress(document_id: str):
    """
    Get progress for a document including
    completed actions and recalculated score.
    """
    progress_col = _get_progress_collection()
    doc_col = _get_documents_collection()

    progress_doc = await progress_col.find_one({"document_id": document_id})
    completed_actions: List[str] = (
        progress_doc.get("completed_actions", []) if progress_doc else []
    )

    # Fetch document for recalculation
    doc = await doc_col.find_one({"document_id": document_id})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Document not found"},
        )

    ocr_text = doc.get("ocr_result", {}).get("text", "")
    scheme_id = doc.get("classification", {}).get("scheme_id", "unknown")
    total_actions = len(doc.get("score_result", {}).get("missing_fields", [])) + \
                    len(doc.get("score_result", {}).get("missing_documents", []))
    completed_count = len(completed_actions)
    completion_pct = round((completed_count / total_actions * 100) if total_actions > 0 else 100)

    # Recalculate score with completed actions
    updated_score = _recalculate_score(ocr_text, scheme_id, completed_actions)

    ready_to_submit = updated_score["score"] >= 90

    return {
        "success": True,
        "data": {
            "document_id": document_id,
            "completed_actions": completed_actions,
            "completion_percentage": completion_pct,
            "ready_to_submit": ready_to_submit,
            "updated_score": updated_score["score"],
            "updated_risk_level": updated_score["risk_level"],
            "updated_missing_fields": updated_score["missing_fields"],
            "updated_missing_documents": updated_score["missing_documents"],
        },
    }


@router.post("/progress/{document_id}/complete/{action_id}")
async def complete_action(document_id: str, action_id: str):
    """
    Mark a specific action item as completed and return
    recalculated score.
    """
    progress_col = _get_progress_collection()
    doc_col = _get_documents_collection()

    # Fetch document
    doc = await doc_col.find_one({"document_id": document_id})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Document not found"},
        )

    # Add to completed
    await progress_col.update_one(
        {"document_id": document_id},
        {"$addToSet": {"completed_actions": action_id}},
        upsert=True,
    )

    progress_doc = await progress_col.find_one({"document_id": document_id})
    completed_actions: List[str] = progress_doc.get("completed_actions", [])

    ocr_text = doc.get("ocr_result", {}).get("text", "")
    scheme_id = doc.get("classification", {}).get("scheme_id", "unknown")
    total_actions = len(doc.get("score_result", {}).get("missing_fields", [])) + \
                    len(doc.get("score_result", {}).get("missing_documents", []))
    completed_count = len(completed_actions)
    completion_pct = round((completed_count / total_actions * 100) if total_actions > 0 else 100)

    # Recalculate score
    updated_score = _recalculate_score(ocr_text, scheme_id, completed_actions)

    ready_to_submit = updated_score["score"] >= 90

    return {
        "success": True,
        "data": {
            "document_id": document_id,
            "completed_actions": completed_actions,
            "completion_percentage": completion_pct,
            "ready_to_submit": ready_to_submit,
            "updated_score": updated_score["score"],
            "updated_risk_level": updated_score["risk_level"],
            "updated_missing_fields": updated_score["missing_fields"],
            "updated_missing_documents": updated_score["missing_documents"],
        },
    }
