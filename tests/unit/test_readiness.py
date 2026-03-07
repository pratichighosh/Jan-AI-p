from app.core.scoring.readiness import calculate_readiness_score, extract_fields_from_text


def test_extract_aadhaar_number():
    text = "Aadhaar Number: 1234 5678 9012"
    fields = extract_fields_from_text(text)
    assert "aadhaar_number" in fields
    assert "9012" in fields["aadhaar_number"]["value"].replace(" ", "")


def test_extract_mobile_number():
    text = "Mobile: 9090001234"
    fields = extract_fields_from_text(text)
    assert "mobile_number" in fields


def test_extract_ifsc_code():
    text = "IFSC Code: SBIN0001234"
    fields = extract_fields_from_text(text)
    assert "ifsc_code" in fields


def test_blank_form_score_is_low():
    text = "PM-KISAN Pradhan Mantri Kisan Samman Nidhi application form"
    result = calculate_readiness_score(text, "pm-kisan")
    assert result["score"] < 50
    assert result["risk_level"] == "HIGH"
    assert len(result["missing_fields"]) > 0
    assert len(result["missing_documents"]) > 0


def test_filled_form_score_is_higher():
    text = (
        "PM-KISAN application form "
        "Applicant Name: Ram Kumar "
        "Father Name: Shyam Kumar "
        "Aadhaar Number: 1234 5678 9012 "
        "Mobile: 9090001234 "
        "Bank Account No: 123456789012 "
        "IFSC Code: SBIN0001234 "
        "Khasra: 12345 "
        "Land Area: 2.5 hectare"
    )
    result = calculate_readiness_score(text, "pm-kisan")
    assert result["score"] > 30
    assert len(result["missing_fields"]) < 8


def test_unknown_scheme_returns_empty_missing():
    text = "some random text"
    result = calculate_readiness_score(text, "unknown-scheme")
    assert result["missing_fields"] == []
    assert result["missing_documents"] == []
