from fastapi import APIRouter, HTTPException
from app.db.mongo import get_documents_collection, get_db
from app.core.scoring.decision import generate_action_items
from app.core.analysis.deadline import extract_deadlines
from app.core.analysis.rejection import is_rejection_notice, extract_rejection_reasons


router = APIRouter(tags=["analysis"])


def _get_progress_collection():
    db = get_db()
    return db["progress"]


@router.get("/analysis/{document_id}")
async def get_analysis(document_id: str):
    """
    Return full analysis for a document:
    - OCR result
    - classification
    - readiness score
    - quality info
    - action items (what user should do next)
    """
    collection = get_documents_collection()
    doc = await collection.find_one({"document_id": document_id})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Document not found"},
        )

    ocr_result = doc.get("ocr_result", {})
    classification = doc.get("classification", {})
    score_result = doc.get("score_result", {})
    quality = doc.get("quality", {})
    language = doc.get("language", "hi")

    missing_fields = score_result.get("missing_fields", [])
    missing_documents = score_result.get("missing_documents", [])
    scheme_id = classification.get("scheme_id", "unknown")

    action_items = generate_action_items(
        scheme_id=scheme_id,
        missing_fields=missing_fields,
        missing_documents=missing_documents,
        language=language,
    )
        # Extract deadlines from OCR text
    raw_ocr_text = ocr_result.get("text", "")
    deadlines = extract_deadlines(raw_ocr_text)

        # Rejection notice analysis
    rejection_reasons = []
    is_rejection = is_rejection_notice(raw_ocr_text)
    if is_rejection:
        rejection_reasons = extract_rejection_reasons(raw_ocr_text)

    # Fetch completed actions from progress collection
    progress_col = _get_progress_collection()
    progress_doc = await progress_col.find_one({"document_id": document_id})
    completed_actions = progress_doc.get("completed_actions", []) if progress_doc else []

    # Mark completed flag on each action item
    for item in action_items:
        item_id = item.get("action_id")
        item["completed"] = item_id in completed_actions

        return {
        "success": True,
        "data": {
            "document_id": doc["document_id"],
            "status": doc.get("status", "UNKNOWN"),
            "language": language,
            "filename": doc.get("filename"),
            "ocr_result": ocr_result,
            "classification": classification,
            "score_result": score_result,
            "quality": quality,
            "action_items": action_items,
            "deadlines": deadlines,
            "is_rejection_notice": is_rejection,
            "rejection_reasons": rejection_reasons,
        },
    }


from app.core.analysis.deadline import extract_deadlines

@router.get("/deadline-test")
async def deadline_test():
    sample_text = """
    Last date to apply: 31/03/2026
    Camp verification date: 15 April 2026
    Date of Birth: 12/05/1985
    Submit your application before 20-04-2026
    """
    result = extract_deadlines(sample_text)
    return {"deadlines": result}

@router.get("/rejection-test")
async def rejection_test():
    sample_text = """
    REJECTION ORDER
    Your application has been rejected due to the following reasons:
    1. Aadhaar verification failed - name mismatch with bank records
    2. Land records invalid - khasra number not found in state database
    3. Bank account number incorrect - IFSC code invalid
    4. Document not attached - income certificate missing
    """
    from app.core.analysis.rejection import is_rejection_notice, extract_rejection_reasons
    is_rejection = is_rejection_notice(sample_text)
    reasons = extract_rejection_reasons(sample_text)
    return {"is_rejection_notice": is_rejection, "rejection_reasons": reasons}


