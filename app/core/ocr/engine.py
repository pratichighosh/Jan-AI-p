# document_pipeline.py
import os
import re
import unicodedata
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import structlog

log = structlog.get_logger()

CONFIDENCE_THRESHOLD = 0.7
MIN_TEXT_LENGTH = 10
MIN_WORDS_FOR_FREE_TEXT = 3
DIGITAL_TEXT_MIN_CHARS = 50

LANG_MAP = {
    "hi": "hi",
    "en": "en",
    "auto": "en",
}


def _upscale_image(file_path: str):
    img = cv2.imread(file_path)
    if img is None:
        return
    h, w = img.shape[:2]
    if max(h, w) < 1200:
        img = cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        cv2.imwrite(file_path, img)


def _crop_top_half(file_path: str) -> Optional[str]:
    img = cv2.imread(file_path)
    if img is None:
        return None
    h, w = img.shape[:2]
    crop = img[0:int(h * 0.55), :]
    base, ext = os.path.splitext(file_path)
    temp_path = f"{base}_top{ext or '.png'}"
    cv2.imwrite(temp_path, crop)
    return temp_path


def extract_text(image_bytes: bytes,
                 filename: str = "document.jpg",
                 language: str = "hi") -> Dict:
    suffix = Path(filename).suffix or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        lang_code = LANG_MAP.get(language.lower(), "en")

        if suffix.lower() == ".pdf":
            ocr_result = _run_pdf_ocr(tmp_path, lang_code)
        else:
            _upscale_image(tmp_path)
            ocr_result = _try_easyocr(tmp_path, lang_code)

        if not ocr_result or not ocr_result.get("text"):
            return {
                "text": "",
                "confidence": 0.0,
                "engine_used": "none",
                "blocks": [],
                "doc_type": "unknown",
                "structured_fields": {},
                "validated_fields": {},
                "success": False,
                "suggestions": [
                    "Upload a clearer image",
                    "Ensure text is not heavily skewed or occluded",
                ],
            }

        cleaned = _clean_text_and_blocks(ocr_result["text"], ocr_result.get("blocks", []))
        text = cleaned["text"]
        blocks = cleaned["blocks"]
        avg_ocr_conf = ocr_result.get("confidence", 0.0)

        doc_type, doc_score, evidence = _classify_document(text)

        structured = {}
        if doc_type in ("aadhaar", "pan", "voter", "passport", "driving"):
            structured = _run_template_extractor(tmp_path, doc_type)

        validation_text = text
        if doc_type == "aadhaar":
            top_path = None
            try:
                top_path = _crop_top_half(tmp_path)
                if top_path:
                    top_ocr = _try_easyocr(top_path, lang_code)
                    top_text = (top_ocr or {}).get("text") or ""
                    if top_text.strip():
                        validation_text = top_text + "\n" + text
            except Exception:
                log.exception("aadhaar_top_half_ocr_failed")
            finally:
                if top_path:
                    try:
                        os.unlink(top_path)
                    except Exception:
                        log.debug("temp_top_crop_cleanup_failed", path=top_path)

        validated, validation_score = _validate_structured_fields(doc_type, structured, validation_text)
        confidence = _compute_confidence(avg_ocr_conf, doc_score, validation_score, structured)
        success = bool(text and (confidence >= 0.0))

        suggestions = []
        if confidence < CONFIDENCE_THRESHOLD:
            suggestions.append("Confidence low — consider reuploading a clearer image or higher resolution.")
        if doc_type == "aadhaar" and not validated.get("aadhaar_number"):
            suggestions.append("Could not reliably detect Aadhaar number. Ensure number is visible and not cropped.")

        return {
            "text": text,
            "confidence": round(confidence, 4),
            "engine_used": ocr_result.get("engine_used", "unknown"),
            "blocks": blocks,
            "doc_type": doc_type,
            "doc_evidence": evidence,
            "structured_fields": structured,
            "validated_fields": validated,
            "success": success,
            "suggestions": suggestions,
        }

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            log.exception("temp_file_cleanup_failed")


# -----------------------
# OCR — EasyOCR only (PaddleOCR removed for cloud deployment)
# -----------------------
def _try_easyocr(file_path: str, lang_code: str) -> Dict:
    try:
        import easyocr
        langs = ["hi", "en"] if lang_code == "hi" else [lang_code, "en"]
        if not hasattr(_try_easyocr, "reader"):
            log.info("easyocr.initializing", langs=langs)
            _try_easyocr.reader = easyocr.Reader(
                langs, gpu=False,
                model_storage_directory="./models",
                download_enabled=True
            )
        raw = _try_easyocr.reader.readtext(file_path)
        if not raw:
            return {"text": "", "confidence": 0.0, "engine_used": "easyocr", "blocks": []}
        blocks, texts, confs = [], [], []
        for item in raw:
            try:
                bbox, text, conf = item
            except Exception:
                continue
            if not text or not text.strip():
                continue
            conf = max(0.0, min(1.0, float(conf)))
            blocks.append({"text": text, "confidence": conf, "bbox": bbox, "engine": "easyocr"})
            texts.append(text)
            confs.append(conf)
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        return {
            "text": "\n".join(texts),
            "confidence": avg_conf * 0.92,
            "engine_used": "easyocr",
            "blocks": blocks
        }
    except Exception as e:
        log.exception("easyocr.exception", error=str(e))
        return {"text": "", "confidence": 0.0, "engine_used": "easyocr", "blocks": [], "error": str(e)}


def _run_pdf_ocr(file_path: str, lang_code: str) -> Dict:
    try:
        import fitz
    except Exception as e:
        log.exception("pdf.pymupdf_import_failed", error=str(e))
        return {"text": "", "confidence": 0.0, "engine_used": "none", "blocks": [], "error_code": "PDF_DECODING_ERROR"}

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        log.exception("pdf.open_failed", error=str(e))
        return {"text": "", "confidence": 0.0, "engine_used": "none", "blocks": [], "error_code": "PDF_DECODING_ERROR"}

    all_text_parts: List[str] = []
    all_blocks: List[Dict] = []
    weighted_conf_sum = 0.0
    total_len = 0

    try:
        for page_index in range(len(doc)):
            page = doc[page_index]
            page_text = ""
            page_conf = 0.0
            page_blocks: List[Dict] = []

            try:
                raw_text = page.get_text("text") or ""
                if raw_text and len(raw_text.strip()) >= DIGITAL_TEXT_MIN_CHARS:
                    page_text = raw_text
                    page_conf = 0.99
                    try:
                        blocks = page.get_text("blocks") or []
                        for b in blocks:
                            if len(b) >= 5:
                                x0, y0, x1, y1, txt = b[:5]
                                if not txt or not str(txt).strip():
                                    continue
                                page_blocks.append({
                                    "text": str(txt),
                                    "confidence": page_conf,
                                    "bbox": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
                                    "engine": "pdf_text_extraction",
                                    "page": page_index,
                                })
                    except Exception:
                        pass
                else:
                    try:
                        pix = page.get_pixmap(dpi=300, alpha=False)
                    except Exception as e:
                        log.exception("pdf.rasterize_failed", page=page_index, error=str(e))
                        continue

                    tmp_img = None
                    try:
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as img_tmp:
                            tmp_img = img_tmp.name
                            pix.save(tmp_img)
                        img_result = _try_easyocr(tmp_img, lang_code)
                        page_text = img_result.get("text", "") or ""
                        page_conf = float(img_result.get("confidence", 0.0) or 0.0)
                        for blk in img_result.get("blocks", []):
                            blk_copy = dict(blk)
                            blk_copy["page"] = page_index
                            page_blocks.append(blk_copy)
                    finally:
                        if tmp_img:
                            try:
                                os.unlink(tmp_img)
                            except Exception:
                                pass

                if not page_text.strip():
                    continue

                all_text_parts.append(page_text)
                all_blocks.extend(page_blocks)
                page_len = len(page_text)
                total_len += page_len
                weighted_conf_sum += page_conf * page_len

            except Exception as e:
                log.exception("pdf.page_processing_failed", page=page_index, error=str(e))
                continue
    finally:
        try:
            doc.close()
        except Exception:
            pass

    if not all_text_parts:
        return {"text": "", "confidence": 0.0, "engine_used": "none", "blocks": [], "error_code": "PDF_NO_TEXT"}

    doc_conf = weighted_conf_sum / total_len if total_len else 0.0
    return {
        "text": "\n\n".join(all_text_parts),
        "confidence": max(0.0, min(1.0, doc_conf)),
        "engine_used": "pdf_mixed",
        "blocks": all_blocks,
    }


# -----------------------
# Text cleanup & helpers
# -----------------------
def _clean_text_and_blocks(raw_text: str, blocks: List[Dict]) -> Dict:
    lines = [ln.strip() for ln in raw_text.splitlines() if ln is not None]
    cleaned_lines = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if not ln:
            i += 1
            continue
        if _is_garbage_text(ln):
            i += 1
            continue
        if re.fullmatch(r"[\d\s\-]{2,}", ln):
            numeric_parts = [re.sub(r"[^\d]", "", ln)]
            j = i + 1
            while j < len(lines) and re.fullmatch(r"[\d\s\-]{1,}", lines[j]) and len(numeric_parts) < 3:
                numeric_parts.append(re.sub(r"[^\d]", "", lines[j]))
                j += 1
            merged = " ".join([p for p in numeric_parts if p])
            cleaned_lines.append(merged)
            i = j
            continue
        cleaned_lines.append(ln)
        i += 1

    final_lines = []
    for ln in cleaned_lines:
        if len(ln) <= 1 and not re.search(r"[\d\u0900-\u097F]", ln):
            continue
        final_lines.append(ln)

    text = "\n".join(final_lines)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = text.strip()

    filtered_blocks = []
    for b in blocks:
        t = b.get("text", "").strip()
        if not t or _is_garbage_text(t):
            continue
        filtered_blocks.append(b)
    return {"text": text, "blocks": filtered_blocks}


def _is_garbage_text(text: str) -> bool:
    if not text:
        return True
    text_len = len(text)
    if text_len == 0:
        return True
    valid_chars = sum(1 for ch in text if unicodedata.category(ch).startswith("L") or unicodedata.category(ch).startswith("N"))
    ratio = valid_chars / text_len
    if re.search(r"(.)\1{8,}", text):
        return True
    if ratio < 0.3:
        if re.fullmatch(r"[\d\s\-]{2,}", text):
            return False
        return True
    return False


# -----------------------
# Classification
# -----------------------
def _classify_document(text: str) -> Tuple[str, float, Dict]:
    t_up = text
    score_map = {}
    evidence = {}

    aadhaar_m = re.search(r"\b(\d{4})\s*(\d{4})\s*(\d{4})\b", t_up)
    if aadhaar_m:
        score_map["aadhaar"] = score_map.get("aadhaar", 0.0) + 0.75
        evidence["aadhaar_number"] = aadhaar_m.group(0)
    if re.search(r"\b(आधार|UIDAI|आम आदमी का अधिकार)\b", t_up):
        score_map["aadhaar"] = score_map.get("aadhaar", 0.0) + 0.15
        evidence.setdefault("keywords", []).append("आधार/UIDAI")

    pan_m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", t_up)
    if pan_m:
        score_map["pan"] = score_map.get("pan", 0.0) + 0.85
        evidence["pan_number"] = pan_m.group(0)
    if re.search(r"\b(INCOME TAX DEPARTMENT|Permanent Account Number|PAN)\b", t_up, flags=re.I):
        score_map["pan"] = score_map.get("pan", 0.0) + 0.1
        evidence.setdefault("keywords", []).append("PAN keywords")

    epic_m = re.search(r"\b([A-Z]{3}\d{7})\b", t_up)
    if epic_m:
        score_map["voter"] = score_map.get("voter", 0.0) + 0.7
        evidence["epic"] = epic_m.group(0)
    if re.search(r"\b(Election Commission|मतदाता|EPIC|Voter)\b", t_up, flags=re.I):
        score_map["voter"] = score_map.get("voter", 0.0) + 0.15
        evidence.setdefault("keywords", []).append("Voter keywords")

    passport_m = re.search(r"\b([A-Z][0-9]{7})\b", t_up)
    if passport_m:
        score_map["passport"] = score_map.get("passport", 0.0) + 0.6
        evidence["passport_no"] = passport_m.group(0)
    if re.search(r"\b(PASSPORT|Passport)\b", t_up):
        score_map["passport"] = score_map.get("passport", 0.0) + 0.2
        evidence.setdefault("keywords", []).append("Passport keyword")

    if re.search(r"\b(DRIVING LICENCE|DL No|Driving Licence|DL)\b", t_up, flags=re.I):
        score_map["driving"] = score_map.get("driving", 0.0) + 0.3
        evidence.setdefault("keywords", []).append("Driving keywords")

    if not score_map:
        return "unknown", 0.0, {}

    best = max(score_map.items(), key=lambda x: x[1])
    return best[0], min(1.0, best[1]), evidence


# -----------------------
# Template extractor
# -----------------------
def _run_template_extractor(file_path: str, doc_type: str) -> Dict:
    try:
        import openbharatocr
    except Exception as e:
        log.debug("openbharat.missing", error=str(e))
        return {}

    mapping = {
        "aadhaar": ["front_aadhaar", "back_aadhaar"],
        "pan": ["pan"],
        "voter": ["voter_id_front", "voter_id_back"],
        "passport": ["passport"],
        "driving": ["driving_licence"],
    }
    results = {}
    for fn_name in mapping.get(doc_type, []):
        try:
            func = getattr(openbharatocr, fn_name, None)
            if not func:
                continue
            raw = func(file_path)
            if raw and isinstance(raw, dict) and any(raw.values()):
                if len(raw.keys()) > len(results.keys()):
                    results = raw
        except Exception as e:
            log.debug("openbharat.extract_failed", fn=fn_name, error=str(e))
    return results or {}


# -----------------------
# Validation & scoring
# -----------------------
def _validate_structured_fields(doc_type: str, structured: Dict, free_text: str) -> Tuple[Dict, float]:
    validated = {}
    score_components = []

    if doc_type == "aadhaar":
        aad = None
        if structured:
            for k, v in structured.items():
                if isinstance(v, str) and re.search(r"\d{4}\s*\d{4}\s*\d{4}", v):
                    aad = re.search(r"\d{4}\s*\d{4}\s*\d{4}", v).group(0)
                    break
        if not aad:
            m = re.search(r"\b(\d{4})\s*(\d{4})\s*(\d{4})\b", free_text)
            if m:
                aad = m.group(0)
        if aad:
            validated["aadhaar_number"] = re.sub(r"\s+", " ", aad).strip()
            score_components.append(1.0)
        else:
            score_components.append(0.0)

        name = structured.get("name") or structured.get("full_name")
        if name and _looks_like_name(name):
            validated["name"] = name
            score_components.append(0.6)
        else:
            alt = _extract_name_from_free_text(free_text)
            if alt:
                validated["name"] = alt
                score_components.append(0.5)
            else:
                score_components.append(0.0)

        dob = structured.get("dob") or structured.get("date_of_birth")
        if not dob:
            m = re.search(r"\b(\d{2}/\d{2}/\d{4}|\d{4})\b", free_text)
            dob = m.group(0) if m else None
        if dob and _validate_dob(dob):
            validated["dob"] = dob
            score_components.append(0.6)
        else:
            score_components.append(0.0)

    if doc_type == "pan":
        pan = structured.get("pan_number") or structured.get("pan")
        if not pan:
            m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", free_text)
            pan = m.group(0) if m else None
        if pan and _validate_pan(pan):
            validated["pan_number"] = pan
            score_components.append(1.0)
        else:
            score_components.append(0.0)
        name = structured.get("name")
        if name and _looks_like_name(name):
            validated["name"] = name
            score_components.append(0.6)
        else:
            score_components.append(0.0)

    if doc_type == "voter":
        epic = structured.get("epic_number")
        if not epic:
            m = re.search(r"\b([A-Z]{3}\d{7})\b", free_text)
            epic = m.group(0) if m else None
        if epic:
            validated["epic"] = epic
            score_components.append(0.9)
        else:
            score_components.append(0.0)

    if doc_type == "passport":
        pno = structured.get("passport_number") or re.search(r"\b([A-Z][0-9]{7})\b", free_text)
        if isinstance(pno, re.Match):
            pno = pno.group(0)
        if pno:
            validated["passport_number"] = pno
            score_components.append(0.8)
        else:
            score_components.append(0.0)

    if doc_type == "driving":
        dl = structured.get("dl_number")
        if not dl:
            m = re.search(r"\b([A-Z0-9\-\/]{6,})\b", free_text)
            dl = m.group(0) if m else None
        if dl:
            validated["dl_number"] = dl
            score_components.append(0.6)
        else:
            score_components.append(0.0)

    if doc_type == "unknown":
        found_any = 0
        if re.search(r"\b(\d{4})\s*(\d{4})\s*(\d{4})\b", free_text):
            validated["aadhaar_number"] = re.search(r"\b(\d{4})\s*(\d{4})\s*(\d{4})\b", free_text).group(0)
            found_any += 1
            score_components.append(0.8)
        if re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", free_text):
            validated["pan_number"] = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", free_text).group(0)
            found_any += 1
            score_components.append(0.8)
        if found_any == 0:
            score_components.append(0.0)

    validation_score = sum(score_components) / len(score_components) if score_components else 0.0
    return validated, max(0.0, min(1.0, validation_score))


def _validate_pan(pan: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan.strip().upper()))


def _validate_dob(dob: str) -> bool:
    dob = dob.strip()
    if re.fullmatch(r"\d{4}", dob):
        return 1900 <= int(dob) <= 2100
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", dob):
        d, m, y = dob.split("/")
        try:
            return 1900 <= int(y) <= 2100 and 1 <= int(m) <= 12 and 1 <= int(d) <= 31
        except Exception:
            return False
    return False


def _looks_like_name(s: str) -> bool:
    s = s.strip()
    letters = sum(1 for ch in s if unicodedata.category(ch).startswith("L"))
    digits = sum(1 for ch in s if unicodedata.category(ch).startswith("N"))
    return letters >= 1 and digits / max(1, len(s)) <= 0.3 and len(s) >= 2


def _extract_name_from_free_text(text: str) -> Optional[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    keywords = {"आधार", "UIDAI", "INCOME", "TAX", "GOVT", "GOVERNMENT", "PAN", "EPIC", "DATE", "DOB"}
    for ln in lines:
        if len(ln) < 3:
            continue
        if any(k in ln.upper() for k in keywords):
            continue
        if _looks_like_name(ln):
            return ln
    return None


def _compute_confidence(ocr_conf: float, doc_score: float, validation_score: float, structured: Dict) -> float:
    ocr_conf = float(ocr_conf or 0.0)
    doc_score = float(doc_score or 0.0)
    validation_score = float(validation_score or 0.0)
    structured_bonus = 0.05 if structured else 0.0
    combined = 0.5 * ocr_conf + 0.2 * doc_score + 0.25 * validation_score + structured_bonus
    return max(0.0, min(1.0, combined))