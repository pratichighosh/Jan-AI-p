from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pymongo import collection
import uuid, structlog
from app.core.preprocessing.image import enhance_image, assess_quality
from app.core.ocr.engine import extract_text
from app.core.analysis.classifier import classify_document
from app.core.scoring.readiness import calculate_readiness_score
from app.db.mongo import get_documents_collection


router = APIRouter(tags=["documents"])
log = structlog.get_logger()

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB

# In-memory store for hackathon — replace with MongoDB in production
_processing_store = {}


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    language: str = Form(default="hi"),
    document_type: str = Form(default=None),
    scheme_id: str = Form(default=None),
):
    # Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_FILE_FORMAT",
                "message": "केवल JPEG, PNG, और PDF फ़ाइलें स्वीकृत हैं",
                "message_en": "Only JPEG, PNG, and PDF files are accepted"
            }
        )

    # Read file
    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_BYTES:
        size_mb = round(len(content) / 1024 / 1024, 1)
        raise HTTPException(
            status_code=413,
            detail={
                "code": "FILE_TOO_LARGE",
                "message": f"फ़ाइल का आकार 10MB से अधिक है (आपकी फ़ाइल: {size_mb}MB)",
                "message_en": f"File exceeds 10MB limit (your file: {size_mb}MB)"
            }
        )

    document_id = f"doc_{uuid.uuid4().hex[:8]}"
    log.info("upload.received", document_id=document_id,
             filename=file.filename, size_bytes=len(content))

    is_pdf = file.content_type == "application/pdf" or (file.filename or "").lower().endswith(".pdf")

    if is_pdf:
        # For PDFs, skip image-based quality checks and enhancement.
        quality = {
            "blur_score": None,
            "brightness": None,
            "resolution": None,
            "score": 100,
            "is_acceptable": True,
            "issues": ["pdf_quality_not_assessed"],
        }
        log.info("upload.quality", document_id=document_id, **quality)
        enhanced = content
    else:
        # Assess quality before enhancement (images only)
        quality = assess_quality(content)
        log.info("upload.quality", document_id=document_id, **quality)

        if not quality["is_acceptable"] and quality["score"] < 10:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "OCR_CONFIDENCE_TOO_LOW",
                    "message": "तस्वीर की गुणवत्ता पर्याप्त नहीं है",
                    "message_en": "Image quality is too poor for text extraction",
                    "issues": quality["issues"],
                    "suggestions": [
                        "Take photo in better lighting",
                        "Hold phone steady to avoid blur",
                        "Ensure all corners of document are visible",
                    ],
                },
            )

        # Enhance image
        try:
            enhanced = enhance_image(content)
        except Exception as e:
            log.error("upload.enhance_failed", error=str(e))
            enhanced = content  # Fall back to original

    # Run OCR
    ocr_result = extract_text(enhanced, filename=file.filename or "document.jpg", language=language)

    classification = classify_document(ocr_result["text"])
    log.info("upload.classified", 
            document_id=document_id,
            doc_type=classification["document_type"],
            scheme=classification["scheme_id"],
            confidence=classification["confidence"])

    # Store result
    # Calculate readiness score
    score_result = calculate_readiness_score(
        ocr_result["text"],
        classification["scheme_id"]
    )

    # Store result in MongoDB
    collection = get_documents_collection()
    document = {
        "document_id": document_id,
        "status": "OCR_COMPLETE",
        "language": language,
        "document_type_hint": document_type,
        "scheme_id_hint": scheme_id,
        "ocr_result": ocr_result,
        "quality": quality,
        "filename": file.filename,
        "classification": classification,
        "score_result": score_result,
    }

    await collection.insert_one(document)

    
    return {
        "success": True,
        "data": {
            "document_id": document_id,
            "status": "OCR_COMPLETE",
            "ocr_confidence": ocr_result["confidence"],
            "engine_used": ocr_result["engine_used"],
            "text_preview": ocr_result["text"][:200] + "..." if len(ocr_result["text"]) > 200 else ocr_result["text"],
            "quality_score": quality["score"],
            "document_type": classification["document_type"],   
            "scheme_detected": classification["scheme_id"],     
            "scheme_confidence": classification["confidence"],
            "readiness_score": score_result["score"],
            "risk_level": score_result["risk_level"],
            "missing_fields": score_result["missing_fields"],
            "missing_documents": score_result["missing_documents"],
        }
    }


@router.get("/documents/{document_id}/ocr")
async def get_ocr_result(document_id: str):
    """Get raw OCR result for a document."""
    collection = get_documents_collection()
    doc = await collection.find_one({"document_id": document_id})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"code": "DOCUMENT_NOT_FOUND", "message": "Document not found"}
        )

    return {"success": True, "data": doc.get("ocr_result", {})}
