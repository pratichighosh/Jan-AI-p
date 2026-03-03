import re

SCHEME_KEYWORDS = {
    "pm-kisan": ["kisan", "किसान", "samman nidhi", "pm-kisan", "pmkisan", "farmer", "khasra", "agricultural"],
    "ayushman-bharat": ["ayushman", "pmjay", "golden card", "health cover", "jan arogya", "आयुष्मान"],
    "ration-card": ["ration", "राशन", "pds", "fair price", "food security", "apl", "bpl", "aay"],
    "aadhaar-services": ["aadhaar", "aadhar", "आधार", "uidai", "biometric", "uid"],
    "social-pension": ["pension", "पेंशन", "old age", "widow", "divyang", "disability", "वृद्धावस्था", "विधवा"],
    "pan-card": ["income tax", "आयकर", "pan", "permanent account", "govt of india", "विभाग"],
}

REJECTION_KEYWORDS = ["rejected", "rejection", "अस्वीकृत", "निरस्त", "not approved", "declined"]
APPROVAL_KEYWORDS = ["approved", "sanctioned", "स्वीकृत", "मंजूर"]


def classify_document(ocr_text: str) -> dict:
    text_lower = ocr_text.lower()

    # Detect document type
    if any(k in text_lower for k in REJECTION_KEYWORDS):
        doc_type = "REJECTION_NOTICE"
    elif any(k in text_lower for k in APPROVAL_KEYWORDS):
        doc_type = "APPROVAL_LETTER"
    else:
        doc_type = "APPLICATION_FORM"

    # Detect scheme
    scores = {}
    for scheme_id, keywords in SCHEME_KEYWORDS.items():
        scores[scheme_id] = sum(1 for k in keywords if k in text_lower)

    best_scheme = max(scores, key=scores.get)
    best_score = scores[best_scheme]

    return {
        "document_type": doc_type,
        "scheme_id": best_scheme if best_score > 0 else "unknown",
        "confidence": min(0.99, best_score * 0.2),
        "all_scores": scores
    }