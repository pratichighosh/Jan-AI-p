# document_pipeline.py
import os
import re
import unicodedata
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading

import cv2
import structlog

log = structlog.get_logger()

# Disable Paddle model connectivity/source checks (must be set before paddleocr import)
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

# Tunables
CONFIDENCE_THRESHOLD = 0.7
MIN_TEXT_LENGTH = 10            # lower threshold — numeric IDs can be short
MIN_WORDS_FOR_FREE_TEXT = 3

# Map user language input to OCR engines' language codes
LANG_MAP = {
    "hi": "hi",
    "en": "en",
    "auto": "en",
}

# Minimum chars to trust digital PDF text and skip raster OCR
DIGITAL_TEXT_MIN_CHARS = 50


_PADDLE_OCR_SINGLETONS: Dict[str, object] = {}
_PADDLE_OCR_LOCK = threading.Lock()


def _get_paddle_ocr(lang_code: str):
    """
    Lazy, per-process singleton for PaddleOCR.
    Keeps model load out of request-path hot loop.
    """
    with _PADDLE_OCR_LOCK:
        existing = _PADDLE_OCR_SINGLETONS.get(lang_code)
        if existing is not None:
            return existing

        from paddleocr import PaddleOCR  # import after env var set at module import time

        paddle_kwargs = {
            "lang": lang_code,
            "device": "cpu",
            "enable_mkldnn": False,
            "cpu_threads": 2,
        }
        if lang_code == "hi":
            paddle_kwargs["text_recognition_model_name"] = "devanagari_PP-OCRv5_server_rec"

        ocr = PaddleOCR(**paddle_kwargs)
        _PADDLE_OCR_SINGLETONS[lang_code] = ocr
        return ocr


def _upscale_image(file_path: str):
    img = cv2.imread(file_path)
    if img is None:
        return
    h, w = img.shape[:2]

    # Only upscale small images
    if max(h, w) < 1200:
        img = cv2.resize(
            img,
            None,
            fx=2.0,
            fy=2.0,
            interpolation=cv2.INTER_CUBIC
        )
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
    """
    High-level pipeline:
      1) OCR (language-aware single pass with fallback)
      2) Text cleanup
      3) Document classification (regex + keywords)
      4) Template-based structured extraction (OpenBharat only after classification)
      5) Field validation
      6) Confidence scoring

    Returns unified dict with keys:
      text, confidence (0-1), engine_used, blocks, doc_type, structured_fields,
      validated_fields, success, suggestions
    """
    suffix = Path(filename).suffix or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name

    try:
        lang_code = LANG_MAP.get(language.lower(), "en")

        # If this is a PDF, use PDF-specific extraction flow
        if suffix.lower() == ".pdf":
            ocr_result = _run_pdf_ocr(tmp_path, lang_code)
        else:
            # 1) Preprocess: upscale small images for better small-font OCR
            _upscale_image(tmp_path)
            # 2) OCR (primary: PaddleOCR, fallback: EasyOCR)
            ocr_result = _run_ocr_with_fallback(tmp_path, lang_code)

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

        # 3) Text cleanup & normalization (preserves Unicode)
        cleaned = _clean_text_and_blocks(ocr_result["text"], ocr_result.get("blocks", []))
        text = cleaned["text"]
        blocks = cleaned["blocks"]
        avg_ocr_conf = ocr_result.get("confidence", 0.0)

        # 4) Document classification from text (regex + keywords)
        doc_type, doc_score, evidence = _classify_document(text)

        # 5) Template-based structured extraction (only for supported types)
        structured = {}
        structured_score = 0.0
        if doc_type in ("aadhaar", "pan", "voter", "passport", "driving"):
            structured = _run_template_extractor(tmp_path, doc_type)
            # structured is {} if extractor not available or failed
        # 6) Aadhaar-specific: crop upper 55% and re-run OCR to improve name / DOB extraction
        validation_text = text
        if doc_type == "aadhaar":
            top_path = None
            try:
                top_path = _crop_top_half(tmp_path)
                if top_path:
                    top_ocr = _run_ocr_with_fallback(top_path, lang_code)
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

        # 7) Field validation
        validated, validation_score = _validate_structured_fields(doc_type, structured, validation_text)

        # 8) Confidence scoring (unified)
        confidence = _compute_confidence(avg_ocr_conf, doc_score, validation_score, structured)

        success = bool(text and (confidence >= 0.0))  # we still return even for low confidence

        # suggestions for user if low confidence or missing key fields
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
# OCR (primary + fallback)
# -----------------------
def _run_ocr_with_fallback(file_path: str, lang_code: str) -> Dict:
    """
    Try PaddleOCR with requested language. If fails or very low output, try EasyOCR.
    Return canonicalized dict: {text, confidence, engine_used, blocks}
    """
    # try Paddle first
    result = _try_paddle(file_path, lang_code)
    if result and result.get("text"):
        # If paddle produced some text, return it (we allow fallback only on complete failure or extremely low conf)
        conf = result.get("confidence", 0.0)
        if conf >= 0.05 or len(result.get("text", "")) >= MIN_TEXT_LENGTH:
            return result
        log.warning("paddle.low_confidence_falling_back", confidence=conf)

    # fallback to EasyOCR
    easy = _try_easyocr(file_path, lang_code)
    if easy and easy.get("text"):
        return easy

    # return paddle result if easyocr didn't produce anything
    return result or easy or {"text": "", "confidence": 0.0, "engine_used": "none", "blocks": []}


def _run_pdf_ocr(file_path: str, lang_code: str) -> Dict:
    """
    End-to-end OCR pipeline for PDFs:
    - Prefer digital text extraction per page
    - Fallback to rasterization + image OCR when needed
    Returns the same canonical dict as image OCR: {text, confidence, engine_used, blocks}.
    """
    try:
        import fitz  # PyMuPDF
    except Exception as e:
        log.exception("pdf.pymupdf_import_failed", error=str(e))
        return {
            "text": "",
            "confidence": 0.0,
            "engine_used": "none",
            "blocks": [],
            "error_code": "PDF_DECODING_ERROR",
            "error": str(e),
        }

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        log.exception("pdf.open_failed", error=str(e))
        return {
            "text": "",
            "confidence": 0.0,
            "engine_used": "none",
            "blocks": [],
            "error_code": "PDF_DECODING_ERROR",
            "error": str(e),
        }

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
                    # Digital text path — authoritative, skip OCR
                    page_text = raw_text
                    page_conf = 0.99

                    # Optional: get positional blocks
                    try:
                        blocks = page.get_text("blocks") or []
                        for b in blocks:
                            if len(b) >= 5:
                                x0, y0, x1, y1, txt = b[:5]
                                if not txt or not str(txt).strip():
                                    continue
                                page_blocks.append(
                                    {
                                        "text": str(txt),
                                        "confidence": page_conf,
                                        "bbox": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
                                        "engine": "pdf_text_extraction",
                                        "page": page_index,
                                    }
                                )
                    except Exception:
                        # If block extraction fails, fall back to plain text only
                        pass
                else:
                    # Rasterization + image OCR path
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

                        # Reuse image OCR pipeline (with language-aware cascade)
                        img_result = _run_ocr_with_fallback(tmp_img, lang_code)
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
                                log.debug("pdf.temp_image_cleanup_failed", path=tmp_img)

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
        return {
            "text": "",
            "confidence": 0.0,
            "engine_used": "none",
            "blocks": [],
            "error_code": "PDF_NO_TEXT",
        }

    doc_conf = weighted_conf_sum / total_len if total_len else 0.0
    return {
        "text": "\n\n".join(all_text_parts),
        "confidence": max(0.0, min(1.0, doc_conf)),
        "engine_used": "pdf_mixed",
        "blocks": all_blocks,
    }

def _try_paddle(file_path: str, lang_code: str) -> Dict:
    try:
        ocr = _get_paddle_ocr(lang_code)

        raw = ocr.ocr(file_path)

        if not raw:
            return {
                "text": "",
                "confidence": 0.0,
                "engine_used": "paddleocr",
                "blocks": []
            }

        blocks = []
        texts = []
        confidences = []

        for page in raw:
            for item in page:
                try:
                    bbox = item[0]
                    text, conf = item[1]
                except Exception:
                    continue

                if not text or not text.strip():
                    continue

                conf = float(conf)
                if conf > 1:
                    conf = conf / 100.0

                conf = max(0.0, min(1.0, conf))

                blocks.append({
                    "text": text,
                    "confidence": conf,
                    "bbox": bbox,
                    "engine": "paddleocr"
                })

                texts.append(text)
                confidences.append(conf)

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "text": "\n".join(texts),
            "confidence": avg_conf,
            "engine_used": "paddleocr",
            "blocks": blocks
        }

    except Exception as e:
        log.exception("paddleocr.exception", error=str(e))
        return {
            "text": "",
            "confidence": 0.0,
            "engine_used": "paddleocr",
            "blocks": [],
            "error": str(e)
        }

# def _try_paddle(file_path: str, lang_code: str) -> Dict:
#     try:
#         from paddleocr import PaddleOCR

#         # PaddleOCR v3+ constructor
#         paddle_kwargs = {
#             "lang": lang_code,          # 'hi' or 'en'
#             "device": "cpu",            # replaces use_gpu
#             "enable_mkldnn": False,
#             "cpu_threads": 2,
#         }
#         if lang_code == "hi":
#             paddle_kwargs["text_recognition_model_name"] = "devanagari_PP-OCRv5_server_rec"

#         ocr = PaddleOCR(**paddle_kwargs)

#         # v3 no longer needs cls=True
#         raw = ocr.ocr(file_path)

#         if not raw:
#             return {
#                 "text": "",
#                 "confidence": 0.0,
#                 "engine_used": "paddleocr",
#                 "blocks": []
#             }

#         blocks = []
#         texts = []
#         confidences = []

#         # v3 returns: [[ [bbox], (text, confidence) ], ...]
#         for page in raw:
#             for item in page:
#                 try:
#                     bbox = item[0]
#                     text, conf = item[1]
#                 except Exception:
#                     continue

#                 if not text or not text.strip():
#                     continue

#                 conf = float(conf)
#                 if conf > 1:
#                     conf = conf / 100.0

#                 conf = max(0.0, min(1.0, conf))

#                 blocks.append({
#                     "text": text,
#                     "confidence": conf,
#                     "bbox": bbox,
#                     "engine": "paddleocr"
#                 })

#                 texts.append(text)
#                 confidences.append(conf)

#         avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

#         return {
#             "text": "\n".join(texts),
#             "confidence": avg_conf,
#             "engine_used": "paddleocr",
#             "blocks": blocks
#         }

#     except Exception as e:
#         log.exception("paddleocr.exception", error=str(e))
#         return {
#             "text": "",
#             "confidence": 0.0,
#             "engine_used": "paddleocr",
#             "blocks": [],
#             "error": str(e)
#         }

def _try_easyocr(file_path: str, lang_code: str) -> Dict:
    try:
        import easyocr
        # prepare languages list for easyocr
        langs = []
        if lang_code == "hi":
            langs = ["hi", "en"]
        else:
            langs = [lang_code, "en"]
        if not hasattr(_try_easyocr, "reader"):
            log.info("easyocr.initializing", langs=langs)
            _try_easyocr.reader = easyocr.Reader(langs, gpu=False, model_storage_directory="./models", download_enabled=True)
        raw = _try_easyocr.reader.readtext(file_path)
        if not raw:
            return {"text": "", "confidence": 0.0, "engine_used": "easyocr", "blocks": []}
        blocks = []
        texts = []
        confs = []
        for item in raw:
            # item: (bbox, text, conf)
            try:
                bbox, text, conf = item
            except Exception:
                continue
            if not text or not text.strip():
                continue
            conf = float(conf)
            conf = max(0.0, min(1.0, conf))
            blocks.append({"text": text, "confidence": conf, "bbox": bbox, "engine": "easyocr"})
            texts.append(text)
            confs.append(conf)
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        # adjust easyocr small bias downward
        adjusted = avg_conf * 0.92
        return {"text": "\n".join(texts), "confidence": adjusted, "engine_used": "easyocr", "blocks": blocks}
    except Exception as e:
        log.exception("easyocr.exception", error=str(e))
        return {"text": "", "confidence": 0.0, "engine_used": "easyocr", "blocks": [], "error": str(e)}


# -----------------------
# Text cleanup & helpers
# -----------------------
def _clean_text_and_blocks(raw_text: str, blocks: List[Dict]) -> Dict:
    """
    Clean OCR raw lines:
     - preserve Unicode letters/digits
     - drop single-character garbage lines except digits (for ID numbers)
     - merge contiguous numeric-only lines into one (useful for Aadhaar 4-4-4 blocks)
     - normalize whitespace
    Returns cleaned dict {text, blocks}
    """
    lines = [ln.strip() for ln in raw_text.splitlines() if ln is not None]
    cleaned_lines = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if not ln:
            i += 1
            continue
        # If line is a single non-letter (trash) skip
        if _is_garbage_text(ln):
            i += 1
            continue
        # Merge numeric-only lines (digit groups) up to 3 consecutive for Aadhaar-like numbers
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

    # Post-process: remove accidental very short lines unless they contain digits or Devanagari letters
    final_lines = []
    for ln in cleaned_lines:
        if len(ln) <= 1 and not re.search(r"[\d\u0900-\u097F]", ln):
            continue
        final_lines.append(ln)

    # Normalize whitespace
    text = "\n".join(final_lines)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = text.strip()
    # blocks: attempt to filter original blocks similarly (best-effort)
    filtered_blocks = []
    for b in blocks:
        t = b.get("text", "").strip()
        if not t:
            continue
        if _is_garbage_text(t):
            continue
        filtered_blocks.append(b)
    return {"text": text, "blocks": filtered_blocks}


def _is_garbage_text(text: str) -> bool:
    """
    Unicode-aware garbage detector:
      - compute ratio of letter/number characters to total
      - detect long repeated-character sequences
    """
    if not text:
        return True
    text_len = len(text)
    if text_len == 0:
        return True

    valid_chars = 0
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("L") or cat.startswith("N"):
            valid_chars += 1
    ratio = valid_chars / text_len
    # repeated pattern
    if re.search(r"(.)\1{8,}", text):  # same char repeated 9+ times
        return True
    # if ascii punctuation-only (no letters/digits)
    if ratio < 0.3:
        # allow short digit-only strings (IDs)
        if re.fullmatch(r"[\d\s\-]{2,}", text):
            return False
        return True
    return False


# -----------------------
# Classification (regex + keywords)
# -----------------------
def _classify_document(text: str) -> Tuple[str, float, Dict]:
    """
    Return (doc_type, score, evidence)
    doc_type: 'aadhaar', 'pan', 'voter', 'passport', 'driving', 'unknown'
    score: 0-1
    evidence: dict listing matches
    """
    t_up = text  # don't uppercase Hindi; keep as-is
    score_map = {}
    evidence = {}

    # Aadhaar: strong 12-digit pattern
    aadhaar_m = re.search(r"\b(\d{4})\s*(\d{4})\s*(\d{4})\b", t_up)
    if aadhaar_m:
        score_map["aadhaar"] = score_map.get("aadhaar", 0.0) + 0.75
        evidence["aadhaar_number"] = aadhaar_m.group(0)

    if re.search(r"\b(आधार|UIDAI|आम आदमी का अधिकार)\b", t_up):
        score_map["aadhaar"] = score_map.get("aadhaar", 0.0) + 0.15
        evidence.setdefault("keywords", []).append("आधार/UIDAI")

    # PAN
    pan_m = re.search(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b", t_up)
    if pan_m:
        score_map["pan"] = score_map.get("pan", 0.0) + 0.85
        evidence["pan_number"] = pan_m.group(0)

    if re.search(r"\b(INCOME TAX DEPARTMENT|Permanent Account Number|PAN)\b", t_up, flags=re.I):
        score_map["pan"] = score_map.get("pan", 0.0) + 0.1
        evidence.setdefault("keywords", []).append("PAN keywords")

    # Voter ID (EPIC)
    epic_m = re.search(r"\b([A-Z]{3}\d{7})\b", t_up)
    if epic_m:
        score_map["voter"] = score_map.get("voter", 0.0) + 0.7
        evidence["epic"] = epic_m.group(0)

    if re.search(r"\b(Election Commission|मतदाता|EPIC|Voter)\b", t_up, flags=re.I):
        score_map["voter"] = score_map.get("voter", 0.0) + 0.15
        evidence.setdefault("keywords", []).append("Voter keywords")

    # Passport (passport number often alphanumeric 7-8 chars)
    passport_m = re.search(r"\b([A-Z][0-9]{7})\b", t_up)
    if passport_m:
        score_map["passport"] = score_map.get("passport", 0.0) + 0.6
        evidence["passport_no"] = passport_m.group(0)

    if re.search(r"\b(PASSPORT|Passport)\b", t_up):
        score_map["passport"] = score_map.get("passport", 0.0) + 0.2
        evidence.setdefault("keywords", []).append("Passport keyword")

    # Driving licence (varies by state; look for DL or "Driving Licence")
    if re.search(r"\b(DRIVING LICENCE|DL No|Driving Licence|DL)\b", t_up, flags=re.I):
        score_map["driving"] = score_map.get("driving", 0.0) + 0.3
        evidence.setdefault("keywords", []).append("Driving keywords")

    if not score_map:
        return "unknown", 0.0, {}

    # choose best by max score
    best = max(score_map.items(), key=lambda x: x[1])
    # clamp score to 1.0
    doc_type = best[0]
    score = min(1.0, best[1])
    return doc_type, score, evidence


# -----------------------
# Template extractor (OpenBharat) - run only after classification
# -----------------------
def _run_template_extractor(file_path: str, doc_type: str) -> Dict:
    """
    Call OpenBharat extractor only for the given doc_type.
    Map doc_type (aadhaar -> front/back ambiguity) to the most likely function.
    Returns structured_fields dict (may be empty).
    """
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
    candidates = mapping.get(doc_type, [])
    results = {}
    for fn_name in candidates:
        try:
            func = getattr(openbharatocr, fn_name, None)
            if not func:
                continue
            raw = func(file_path)
            if raw and isinstance(raw, dict) and any(raw.values()):
                # prefer richer result (more keys)
                if len(raw.keys()) > len(results.keys()):
                    results = raw
        except Exception as e:
            log.debug("openbharat.extract_failed", fn=fn_name, error=str(e))
            continue
    return results or {}


# -----------------------
# Validation & scoring
# -----------------------
def _validate_structured_fields(doc_type: str, structured: Dict, free_text: str) -> Tuple[Dict, float]:
    """
    Validate fields found by template extractor and also attempt regex extraction from free_text
    Returns (validated_fields, validation_score 0-1)
    """
    validated = {}
    score_components = []
    # Aadhaar
    if doc_type == "aadhaar":
        # find aadhaar in structured or free_text
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
            aad_norm = re.sub(r"\s+", " ", aad).strip()
            validated["aadhaar_number"] = aad_norm
            score_components.append(1.0)
        else:
            score_components.append(0.0)

        # name
        name = structured.get("name") or structured.get("full_name")
        if name and _looks_like_name(name):
            validated["name"] = name
            score_components.append(0.6)
        else:
            # try heuristic: first non-numeric, non-keyword line
            alt = _extract_name_from_free_text(free_text)
            if alt:
                validated["name"] = alt
                score_components.append(0.5)
            else:
                score_components.append(0.0)

        # dob
        dob = structured.get("dob") or structured.get("date_of_birth")
        if not dob:
            m = re.search(r"\b(\d{2}/\d{2}/\d{4}|\d{4})\b", free_text)
            dob = m.group(0) if m else None
        if dob and _validate_dob(dob):
            validated["dob"] = dob
            score_components.append(0.6)
        else:
            score_components.append(0.0)

    # PAN
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

        # name
        name = structured.get("name")
        if name and _looks_like_name(name):
            validated["name"] = name
            score_components.append(0.6)
        else:
            score_components.append(0.0)

    # Voter / Passport / Driving basic checks: look for expected IDs
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

    # If no specific doc_type (unknown) try to at least check for strong identifiers
    if doc_type == "unknown":
        # try to find pan/aadhaar as strong signal
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

    # final validation score - average of components (if none, return 0)
    validation_score = sum(score_components) / len(score_components) if score_components else 0.0
    return validated, max(0.0, min(1.0, validation_score))


# -----------------------
# Utility validators & extractors
# -----------------------
def _validate_pan(pan: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", pan.strip().upper()))


def _validate_dob(dob: str) -> bool:
    dob = dob.strip()
    if re.fullmatch(r"\d{4}", dob):
        year = int(dob)
        return 1900 <= year <= 2100
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", dob):
        d, m, y = dob.split("/")
        try:
            dd, mm, yy = int(d), int(m), int(y)
        except Exception:
            return False
        return 1900 <= yy <= 2100 and 1 <= mm <= 12 and 1 <= dd <= 31
    return False


def _looks_like_name(s: str) -> bool:
    s = s.strip()
    # name heuristic: contains letters (including Devanagari), not mostly digits, length reasonable
    letters = sum(1 for ch in s if unicodedata.category(ch).startswith("L"))
    digits = sum(1 for ch in s if unicodedata.category(ch).startswith("N"))
    if letters < 1:
        return False
    if digits / max(1, len(s)) > 0.3:
        return False
    if len(s) < 2:
        return False
    return True


def _extract_name_from_free_text(text: str) -> Optional[str]:
    # heuristics: pick first long line that is not a keyword and contains letters
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    keywords = {"आधार", "UIDAI", "INCOME", "TAX", "GOVT", "GOVERNMENT", "PAN", "EPIC", "DATE", "DOB"}
    for ln in lines:
        if len(ln) < 3:
            continue
        up = ln.upper()
        if any(k in up for k in keywords):
            continue
        if _looks_like_name(ln):
            return ln
    return None


def _compute_confidence(ocr_conf: float, doc_score: float, validation_score: float, structured: Dict) -> float:
    """
    Weighted combination:
      - ocr_conf: 50%
      - doc_score (classification from regex/keywords): 20%
      - validation_score (field validations): 25%
      - structured presence bonus: 5%
    """
    ocr_conf = float(ocr_conf or 0.0)
    doc_score = float(doc_score or 0.0)
    validation_score = float(validation_score or 0.0)
    structured_bonus = 0.05 if structured else 0.0
    combined = 0.5 * ocr_conf + 0.2 * doc_score + 0.25 * validation_score + structured_bonus
    # clamp
    return max(0.0, min(1.0, combined))
