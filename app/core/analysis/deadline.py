import re
from datetime import datetime, date
from typing import List, Dict, Any


# All common date formats found in Indian government documents
DATE_PATTERNS = [
    # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    (r"\b(\d{2})[\/\-\.](\d{2})[\/\-\.](\d{4})\b", "dmy"),
    # YYYY-MM-DD
    (r"\b(\d{4})[\/\-\.](\d{2})[\/\-\.](\d{2})\b", "ymd"),
    # DD Month YYYY  e.g. 15 March 2025
    (
        r"\b(\d{1,2})\s+"
        r"(january|february|march|april|may|june|july|august|"
        r"september|october|november|december|"
        r"jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)"
        r"\s+(\d{4})\b",
        "dmonthy",
    ),
    # Month DD, YYYY  e.g. March 15, 2025
    (
        r"\b(january|february|march|april|may|june|july|august|"
        r"september|october|november|december|"
        r"jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)"
        r"\s+(\d{1,2})[,\s]+(\d{4})\b",
        "monthdY",
    ),
]


MONTH_MAP = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


# Keywords that suggest a date is a deadline
DEADLINE_KEYWORDS = [
    r"\bbefore\b",                   # standalone "before" anywhere in context
    r"last\s+date",
    r"deadline",
    r"due\s+date",
    r"submit\s+by",
    r"apply\s+before",
    r"submit.*before",
    r"application.*before",
    r"expire[sd]?",
    r"expiry",
    r"valid\s+till",
    r"valid\s+upto",
    r"last\s+day",
    r"अंतिम\s+तिथि",
    r"जमा\s+करने\s+की\s+तिथि",
]


# Keywords that suggest a date is an event
EVENT_KEYWORDS = [
    r"camp",
    r"hearing",
    r"interview",
    r"verification\s+date",
    r"verification",
    r"inspection",
    r"survey",
    r"shivir",
    r"शिविर",
]


# Keywords that suggest a date is purely informational
INFORMATIONAL_PATTERNS = [
    r"date\s+of\s+birth",
    r"dob",
    r"born\s+on",
    r"जन्म\s+तिथि",
    r"issue\s+date",
    r"issued\s+on",
    r"registration\s+date",
    r"application\s+date",
    r"date\s+of\s+issue",
]


def _parse_date(match, fmt: str):
    """Parse a regex match into a date object."""
    try:
        if fmt == "dmy":
            d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
        elif fmt == "ymd":
            y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
        elif fmt == "dmonthy":
            d = int(match.group(1))
            m = MONTH_MAP.get(match.group(2).lower(), 0)
            y = int(match.group(3))
        elif fmt == "monthdY":
            m = MONTH_MAP.get(match.group(1).lower(), 0)
            d = int(match.group(2))
            y = int(match.group(3))
        else:
            return None

        if m == 0 or not (1 <= d <= 31) or not (1900 <= y <= 2100):
            return None
        return date(y, m, d)
    except (ValueError, AttributeError):
        return None


def _classify_date(text_around: str, match_start: int, full_text: str) -> str:
    """
    Classify date as DEADLINE, EVENT, or INFORMATIONAL.

    Strategy:
    - Use 200 chars BEFORE the date as primary signal.
    - Use 20 chars AFTER for informational check only.
    - Informational checked first (highest priority).
    - Event checked before Deadline (more specific).
    """
    # 200 chars before the date
    before = full_text[max(0, match_start - 200): match_start].lower()
    # 20 chars after for "date of birth" type patterns
    after = full_text[match_start: min(len(full_text), match_start + 20)].lower()
    combined_for_info = before + after

    # 1. INFORMATIONAL first — highest priority
    for pat in INFORMATIONAL_PATTERNS:
        if re.search(pat, combined_for_info):
            return "INFORMATIONAL"

    # 2. EVENT before DEADLINE — more specific wins
    for pat in EVENT_KEYWORDS:
        if re.search(pat, before):
            return "EVENT"

    # 3. DEADLINE
    for pat in DEADLINE_KEYWORDS:
        if re.search(pat, before):
            return "DEADLINE"

    return "INFORMATIONAL"


def extract_deadlines(ocr_text: str) -> List[Dict[str, Any]]:
    """
    Extract all dates from OCR text, classify them,
    compute days remaining, and sort nearest first.

    Returns list sorted by:
    - Classification: DEADLINE first, EVENT second, INFORMATIONAL last
    - Then by days_remaining ascending (nearest first)
    """
    text = ocr_text.lower()
    today = date.today()
    found = []
    seen_dates = set()

    for pattern, fmt in DATE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            parsed = _parse_date(match, fmt)
            if parsed is None:
                continue
            if parsed in seen_dates:
                continue
            seen_dates.add(parsed)

            classification = _classify_date(
                text_around=text,
                match_start=match.start(),
                full_text=text,
            )

            days_remaining = (parsed - today).days

            # Context snippet for display
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            context = text[start:end]

            found.append({
                "date": parsed.strftime("%d/%m/%Y"),
                "date_iso": parsed.isoformat(),
                "classification": classification,
                "days_remaining": days_remaining,
                "is_past": days_remaining < 0,
                "is_urgent": 0 <= days_remaining <= 7,
                "context_snippet": context.strip()[:100],
            })

    # Sort: DEADLINE → EVENT → INFORMATIONAL, then nearest first
    found.sort(
        key=lambda x: (
            0 if x["classification"] == "DEADLINE" else
            1 if x["classification"] == "EVENT" else 2,
            x["days_remaining"],
        )
    )

    return found
