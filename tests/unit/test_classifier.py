from app.core.analysis.classifier import classify_document


def test_classify_pm_kisan():
    text = "PM-KISAN Pradhan Mantri Kisan Samman Nidhi application form khasra land record"
    result = classify_document(text)
    assert result["scheme_id"] == "pm-kisan"
    assert result["confidence"] > 0
    assert result["document_type"] == "APPLICATION_FORM"


def test_classify_ayushman_bharat():
    text = "Ayushman Bharat Pradhan Mantri Jan Arogya Yojana PMJAY golden card health insurance"
    result = classify_document(text)
    assert result["scheme_id"] == "ayushman-bharat"
    assert result["confidence"] > 0


def test_classify_ration_card():
    text = "Ration Card NFSA National Food Security Act below poverty line BPL fair price shop"
    result = classify_document(text)
    assert result["scheme_id"] == "ration-card"
    assert result["confidence"] > 0


def test_classify_aadhaar_services():
    text = "UIDAI Aadhaar correction form demographic update name correction address correction"
    result = classify_document(text)
    assert result["scheme_id"] == "aadhaar-services"
    assert result["confidence"] > 0


def test_classify_social_pension():
    text = "old age pension NSAP Indira Gandhi National social pension application form"
    result = classify_document(text)
    assert result["scheme_id"] == "social-pension"
    assert result["confidence"] > 0


def test_classify_pan_card():
    text = "Permanent Account Number PAN card Form 49A Income Tax Department NSDL application"
    result = classify_document(text)
    assert result["scheme_id"] == "pan-card"
    assert result["confidence"] > 0


def test_classify_unknown():
    text = "This is a random document with no relevant keywords at all"
    result = classify_document(text)
    assert result["scheme_id"] == "unknown"


def test_classify_rejection_notice():
    text = "Your application has been rejected. You are not eligible for this scheme."
    result = classify_document(text)
    assert result["document_type"] == "REJECTION_NOTICE"
