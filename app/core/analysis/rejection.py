import re
from typing import List, Dict, Any


# Rejection reason patterns for Indian government documents
REJECTION_PATTERNS = [
    {
        "reason_id": "incomplete_form",
        "pattern": r"(incomplete|not\s+filled|blank\s+field|missing\s+information|अधूरा|अपूर्ण)",
        "title": "Incomplete form",
        "remediation": "Fill all mandatory fields in the form completely before resubmitting.",
        "priority": 1,
    },
    {
        "reason_id": "invalid_aadhaar",
        "pattern": r"(invalid\s+aadhaar|aadhaar\s+not\s+valid|aadhaar\s+mismatch|aadhaar\s+verification\s+failed)",
        "title": "Invalid or mismatched Aadhaar",
        "remediation": "Verify your Aadhaar number carefully. Ensure name and date of birth match Aadhaar exactly.",
        "priority": 1,
    },
    {
        "reason_id": "bank_details_mismatch",
        "pattern": r"(bank\s+account.*invalid|invalid.*bank|account\s+number.*incorrect|ifsc.*invalid|bank\s+details.*mismatch)",
        "title": "Invalid or mismatched bank details",
        "remediation": "Cross-check account number and IFSC from your bank passbook. Ensure account is in applicant's name.",
        "priority": 1,
    },
    {
        "reason_id": "land_records_invalid",
        "pattern": r"(land\s+record.*invalid|invalid.*land|khasra.*not\s+found|land\s+ownership.*not\s+verified|भूमि\s+रिकॉर्ड)",
        "title": "Land records invalid or not verified",
        "remediation": "Obtain updated land records from your tehsil office or state land portal. Ensure khasra number is correct.",
        "priority": 1,
    },
    {
        "reason_id": "not_eligible",
        "pattern": r"(not\s+eligible|ineligible|does\s+not\s+meet|eligibility\s+criteria.*not|पात्र\s+नहीं)",
        "title": "Eligibility criteria not met",
        "remediation": "Review the eligibility criteria for this scheme carefully. Check income limit, age, and category requirements.",
        "priority": 1,
    },
    {
        "reason_id": "document_missing",
        "pattern": r"(document.*not\s+attached|missing\s+document|document.*not\s+submitted|दस्तावेज़.*नहीं)",
        "title": "Required document not attached",
        "remediation": "Attach all required supporting documents. Check the scheme guidelines for the complete document list.",
        "priority": 1,
    },
    {
        "reason_id": "document_expired",
        "pattern": r"(document.*expired|expired.*document|validity.*expired|दस्तावेज़.*समाप्त)",
        "title": "Document expired",
        "remediation": "Renew the expired document before reapplying. Check expiry dates on all submitted documents.",
        "priority": 1,
    },
    {
        "reason_id": "duplicate_application",
        "pattern": r"(duplicate\s+application|already\s+registered|already\s+applied|previously\s+submitted|डुप्लीकेट)",
        "title": "Duplicate application",
        "remediation": "You may already be registered. Check your application status online before submitting again.",
        "priority": 2,
    },
    {
        "reason_id": "photo_mismatch",
        "pattern": r"(photo.*mismatch|photograph.*not\s+clear|photo.*not\s+matching|फोटो.*मेल\s+नहीं)",
        "title": "Photo mismatch or unclear",
        "remediation": "Submit a recent clear passport-size photograph. Ensure photo matches other identity documents.",
        "priority": 2,
    },
    {
        "reason_id": "signature_missing",
        "pattern": r"(signature.*missing|not\s+signed|unsigned|हस्ताक्षर.*नहीं)",
        "title": "Signature missing",
        "remediation": "Sign the application form at all required places before resubmitting.",
        "priority": 2,
    },
    {
        "reason_id": "address_mismatch",
        "pattern": r"(address.*mismatch|address.*not\s+matching|address.*incorrect|पता.*मेल\s+नहीं)",
        "title": "Address mismatch",
        "remediation": "Ensure address on the form matches exactly with your address proof document.",
        "priority": 2,
    },
    {
        "reason_id": "income_limit_exceeded",
        "pattern": r"(income.*exceeds|income.*above\s+limit|income.*not\s+eligible|आय\s+सीमा\s+से\s+अधिक)",
        "title": "Income exceeds scheme limit",
        "remediation": "This scheme has an income eligibility limit. Obtain an updated income certificate from a competent authority.",
        "priority": 2,
    },
    {
        "reason_id": "name_mismatch",
        "pattern": r"(name.*mismatch|name.*not\s+matching|name.*differs|नाम.*मेल\s+नहीं)",
        "title": "Name mismatch across documents",
        "remediation": "Ensure your name is spelled identically across Aadhaar, bank passbook, and the application form.",
        "priority": 2,
    },
]


REJECTION_DOCUMENT_INDICATORS = [
    r"your\s+application\s+has\s+been\s+rejected",
    r"rejection\s+order",
    r"regret\s+to\s+inform",
    r"application.*rejected",
    r"not\s+approved",
    r"refused",
    r"अस्वीकार",
    r"निरस्त",
    r"आवेदन\s+अस्वीकृत",
]


def is_rejection_notice(ocr_text: str) -> bool:
    """
    Returns True if the document appears to be a rejection notice.
    """
    text = ocr_text.lower()
    return any(
        re.search(pat, text)
        for pat in REJECTION_DOCUMENT_INDICATORS
    )


def extract_rejection_reasons(ocr_text: str) -> List[Dict[str, Any]]:
    """
    Extract rejection reasons from OCR text and generate
    remediation action items for each.

    Returns list of reasons sorted by priority.
    """
    text = ocr_text.lower()
    found = []
    seen = set()

    for rule in REJECTION_PATTERNS:
        if rule["reason_id"] in seen:
            continue
        if re.search(rule["pattern"], text, re.IGNORECASE):
            seen.add(rule["reason_id"])

            # Get context snippet around the match
            match = re.search(rule["pattern"], text, re.IGNORECASE)
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            snippet = text[start:end].strip()[:120]

            found.append({
                "reason_id": rule["reason_id"],
                "title": rule["title"],
                "remediation": rule["remediation"],
                "priority": rule["priority"],
                "context_snippet": snippet,
                "action_id": f"rejection_{rule['reason_id']}",
            })

    # Sort by priority ascending (1 = critical first)
    found.sort(key=lambda x: x["priority"])
    return found
