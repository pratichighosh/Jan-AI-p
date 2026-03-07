import re

from app.core.scoring.schemes import (
    get_scheme_weights,
    get_required_fields,
    get_required_documents,
)


# Regex patterns to detect fields in OCR text
FIELD_PATTERNS = {
    # ── Common fields ──────────────────────────────────────────────────────
    "applicant_name": (
        r"(applicant['\s]*s?\s*name|name\s+of\s+applicant"
        r"|full\s+name|नाम|आवेदक\s+का\s+नाम)\s*[:\-]?\s*"
        r"([A-Za-z\u0900-\u097F\s]{3,40})"
    ),
    "father_name": (
        r"(father['\s]*s?\s*name|पिता\s+का\s+नाम|पिता"
        r"|s/o|son\s+of|d/o|daughter\s+of|w/o|wife\s+of)"
        r"\s*[:\-]?\s*([A-Za-z\u0900-\u097F\s]{3,40})"
    ),
    "date_of_birth": (
        r"(date\s+of\s+birth|dob|जन्म\s+तिथि|जन्मतिथि)"
        r"\s*[:\-]?\s*(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})"
        r"|\b(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})\b"
    ),
    "aadhaar_number": (
        r"\b\d{4}\s?\d{4}\s?\d{4}\b"
    ),
    "pan_number": (
        r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"
    ),
    "mobile_number": (
        r"(mobile|phone|contact|mob|फोन|मोबाइल)"
        r"\s*[:\-]?\s*([6-9]\d{9})"
        r"|\b([6-9]\d{9})\b"
    ),
    "bank_account": (
        r"(account\s+no|account\s+number|a/c\s+no"
        r"|खाता\s+संख्या|बैंक\s+खाता)"
        r"\s*[:\-]?\s*(\d{9,18})"
    ),
    "ifsc_code": (
        r"(ifsc|ifsc\s+code|आईएफएससी)"
        r"\s*[:\-]?\s*([A-Z]{4}0[A-Z0-9]{6})"
        r"|\b([A-Z]{4}0[A-Z0-9]{6})\b"
    ),
    "pincode": (
        r"(pin\s*code|pincode|postal\s+code|पिन\s+कोड)"
        r"\s*[:\-]?\s*(\d{6})"
        r"|\b(\d{6})\b"
    ),
    "address": (
        r"(address|permanent\s+address|residential\s+address"
        r"|पता|स्थायी\s+पता)\s*[:\-]?\s*"
        r"([A-Za-z\u0900-\u097F0-9\s,\.\-]{10,100})"
    ),

    # ── PM-KISAN specific ──────────────────────────────────────────────────
    "khasra_number": (
        r"(khasra|khasra\s+no|खसरा|खसरा\s+संख्या)"
        r"\s*[:\-]?\s*(\d{1,8})"
    ),
    "land_area": (
        r"(land\s+area|area|क्षेत्रफल|hectare|हेक्टेयर"
        r"|acre|एकड़)\s*[:\-]?\s*([\d\.]+)"
    ),

    # ── Ayushman Bharat specific ───────────────────────────────────────────
    "family_members": (
        r"(family\s+members|number\s+of\s+members"
        r"|परिवार\s+के\s+सदस्य|सदस्यों\s+की\s+संख्या)"
        r"\s*[:\-]?\s*(\d{1,2})"
    ),
    "income_level": (
        r"(annual\s+income|income|वार्षिक\s+आय|आय)"
        r"\s*[:\-]?\s*(rs\.?\s*[\d,]+|₹\s*[\d,]+|[\d,]+)"
    ),

    # ── Social Pension specific ────────────────────────────────────────────
    "pension_type": (
        r"(pension\s+type|type\s+of\s+pension|पेंशन\s+प्रकार"
        r"|old\s+age|widow|disability|divyang)"
    ),

    # ── Aadhaar Services specific ──────────────────────────────────────────
    "correction_field": (
        r"(correction\s+in|field\s+to\s+be\s+corrected"
        r"|सुधार|नाम\s+सुधार|पता\s+सुधार"
        r"|name\s+correction|address\s+correction|dob\s+correction)"
    ),
}



def extract_fields_from_text(ocr_text: str) -> dict:
    """Detect which fields are present in OCR text using regex."""
    found = {}
    for field_id, pattern in FIELD_PATTERNS.items():
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            found[field_id] = {
                "found": True,
                "value": match.group(0)[:50],  # cap length
            }
    return found


def calculate_readiness_score(
    ocr_text: str,
    scheme_id: str,
    uploaded_docs: list = None,
    completed_action_fields: list = None,  # NEW
) -> dict:
    uploaded_docs = uploaded_docs or []
    completed_action_fields = completed_action_fields or []  # NEW

    try:
        required_fields = get_required_fields(scheme_id)
        required_docs = get_required_documents(scheme_id)
        weights = get_scheme_weights(scheme_id)
    except FileNotFoundError:
        required_fields = []
        required_docs = []
        weights = {
            "fields_complete": 0.60,
            "docs_present": 0.30,
            "validation_pass": 0.10,
        }

    w_fields = weights.get("fields_complete", 0.60)
    w_docs = weights.get("docs_present", 0.30)
    w_val = weights.get("validation_pass", 0.10)

    # Component 1 — fields
    found_fields = extract_fields_from_text(ocr_text)

    # Count completed action fields as found too
    for f in completed_action_fields:
        if f not in found_fields:
            found_fields[f] = {"found": True, "value": "(completed by user)"}

    completed_fields = [f for f in required_fields if f in found_fields]
    field_score = (
        len(completed_fields) / len(required_fields)
        if required_fields else 1.0
    )

    # Component 2 — documents
    present_docs = [d for d in required_docs if d in uploaded_docs]
    doc_score = (
        len(present_docs) / len(required_docs)
        if required_docs else 0.0
    )

    # Component 3 — validation
    validation_checks = []
    if "aadhaar_number" in found_fields:
        val = found_fields["aadhaar_number"]["value"].replace(" ", "")
        if val != "(completed by user)":
            validation_checks.append(len(val) == 12 and val.isdigit())
    if "pan_number" in found_fields:
        val = found_fields["pan_number"]["value"]
        if val != "(completed by user)":
            validation_checks.append(
                bool(re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", val))
            )
    if "mobile_number" in found_fields:
        val = found_fields["mobile_number"]["value"]
        if val != "(completed by user)":
            validation_checks.append(bool(re.match(r"^[6-9]\d{9}$", val)))

    val_score = (
        sum(validation_checks) / len(validation_checks)
        if validation_checks else 0.5
    )

    raw = (field_score * w_fields) + (doc_score * w_docs) + (val_score * w_val)
    final_score = round(raw * 100)

    if final_score >= 90:
        risk = "LOW"
    elif final_score >= 70:
        risk = "MEDIUM"
    else:
        risk = "HIGH"

    missing_fields = [f for f in required_fields if f not in found_fields]
    missing_docs = [d for d in required_docs if d not in uploaded_docs]

    return {
        "score": final_score,
        "risk_level": risk,
        "components": {
            "fields": round(field_score * w_fields * 100),
            "documents": round(doc_score * w_docs * 100),
            "validation": round(val_score * w_val * 100),
            "fields_detail": f"{len(completed_fields)}/{len(required_fields)} fields found",
            "docs_detail": f"{len(present_docs)}/{len(required_docs)} documents uploaded",
        },
        "missing_fields": missing_fields,
        "missing_documents": missing_docs,
        "found_fields": found_fields,
    }
