import re
from typing import Dict, Tuple


# Simple keyword-based rules for schemes
SCHEME_KEYWORDS: Dict[str, Dict[str, list[str]]] = {
    "pm-kisan": {
        "must": [
            r"pradhan\s+mantri\s+kisan\s+samman\s+nidhi",
            r"pm[-\s]?kisan",
            r"kisan\s+samman",
        ],
        "boost": [
            r"small\s+and\s+marginal\s+landholding",
            r"farmer\s+families",
            r"2\s*ha\s+of\s+cultivable\s+land",
            r"khasra",
            r"land\s+record",
            r"agricultural\s+land",
            r"cultivable",
        ],
    },
    "ayushman-bharat": {
        "must": [
            r"ayushman\s+bharat",
            r"pradhan\s+mantri\s+jan\s+arogya",
            r"pmjay",
        ],
        "boost": [
            r"golden\s+card",
            r"health\s+insurance",
            r"sehat",
            r"hospitalization",
            r"empanelled\s+hospital",
            r"secondary\s+and\s+tertiary\s+care",
        ],
    },
    "ration-card": {
        "must": [
            r"ration\s+card",
            r"nfsa",
            r"national\s+food\s+security",
        ],
        "boost": [
            r"antyodaya",
            r"priority\s+household",
            r"fair\s+price\s+shop",
            r"below\s+poverty\s+line",
            r"bpl",
            r"apl",
            r"food\s+grain",
        ],
    },
    "aadhaar-services": {
        "must": [
            r"uidai",
            r"aadhaar",
            r"unique\s+identification",
        ],
        "boost": [
            r"enrolment\s+form",
            r"correction\s+form",
            r"update\s+aadhaar",
            r"biometric",
            r"demographic\s+update",
            r"aadhaar\s+card\s+correction",
        ],
    },
    "social-pension": {
        "must": [
            r"old\s+age\s+pension",
            r"widow\s+pension",
            r"disability\s+pension",
            r"social\s+pension",
            r"nsap",
        ],
        "boost": [
            r"indira\s+gandhi\s+national",
            r"ignoaps",
            r"ignwps",
            r"igndps",
            r"senior\s+citizen",
            r"divyang",
            r"handicapped",
            r"monthly\s+pension",
        ],
    },
    "pan-card": {
        "must": [
            r"permanent\s+account\s+number",
            r"form\s+49a",
            r"pan\s+card",
        ],
        "boost": [
            r"income\s+tax\s+department",
            r"pan\s+application",
            r"nsdl",
            r"utiitsl",
            r"tin\s+facilitation",
            r"tax\s+payer",
        ],
    },
}

DOCUMENT_TYPE_RULES = {
    "APPLICATION_FORM": [
        r"application\s+form",
        r"registration\s+form",
        r"form\s+no\.",
        r"application\s+for",
        r"apply\s+for",
        r"enrollment\s+form",
        r"please\s+fill",
        r"to\s+be\s+filled",
    ],
    "REJECTION_NOTICE": [
        r"rejection\s+order",
        r"not\s+eligible",
        r"your\s+application\s+has\s+been\s+rejected",
        r"regret\s+to\s+inform",
        r"application\s+rejected",
        r"ineligible",
        r"disqualified",
    ],
    "APPROVAL_LETTER": [
        r"sanction\s+order",
        r"hereby\s+sanctioned",
        r"application\s+approved",
        r"congratulations",
        r"has\s+been\s+approved",
        r"beneficiary\s+approved",
    ],
    "NOTICE": [
        r"notice\s+to",
        r"public\s+notice",
        r"office\s+order",
        r"circular\s+no",
        r"government\s+of\s+india\s+notification",
    ],
}

def classify_document(ocr_text: str) -> Dict:
    """
    Classify document_type and scheme_id using simple keyword scoring.
    """
    text = ocr_text.lower()

    # 1) Document type
    doc_type_scores: Dict[str, int] = {}
    for doc_type, patterns in DOCUMENT_TYPE_RULES.items():
        score = 0
        for pat in patterns:
            if re.search(pat, text):
                score += 1
        doc_type_scores[doc_type] = score

    # default
    best_doc_type = "APPLICATION_FORM"
    if doc_type_scores:
        best_doc_type = max(doc_type_scores, key=doc_type_scores.get)
        if doc_type_scores[best_doc_type] == 0:
            best_doc_type = "APPLICATION_FORM"

    # 2) Scheme detection
    scheme_scores: Dict[str, int] = {}
    for scheme_id, cfg in SCHEME_KEYWORDS.items():
        must_patterns = cfg.get("must", [])
        boost_patterns = cfg.get("boost", [])

        # require at least one MUST to consider
        if not any(re.search(pat, text) for pat in must_patterns):
            scheme_scores[scheme_id] = 0
            continue

        score = 0
        # each MUST hit adds 2 points
        for pat in must_patterns:
            if re.search(pat, text):
                score += 2

        # each BOOST hit adds 1 point
        for pat in boost_patterns:
            if re.search(pat, text):
                score += 1

        scheme_scores[scheme_id] = score

    best_scheme = "unknown"
    best_score = 0
    for sid, sc in scheme_scores.items():
        if sc > best_score:
            best_scheme = sid
            best_score = sc

    # simple confidence: normalized by max possible for that scheme
    confidence = 0.0
    if best_scheme != "unknown":
        cfg = SCHEME_KEYWORDS[best_scheme]
        max_score = 2 * len(cfg.get("must", [])) + len(cfg.get("boost", []))
        confidence = round(best_score / max_score, 2) if max_score > 0 else 0.0

    return {
        "document_type": best_doc_type,
        "scheme_id": best_scheme,
        "confidence": confidence,
        "all_scores": scheme_scores,
    }

