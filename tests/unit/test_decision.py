from app.core.scoring.decision import generate_action_items


def test_action_items_for_missing_fields():
    items = generate_action_items(
        scheme_id="pm-kisan",
        missing_fields=["aadhaar_number", "bank_account"],
        missing_documents=[],
        language="en",
    )
    action_ids = [i["action_id"] for i in items]
    assert "field_aadhaar_number" in action_ids
    assert "field_bank_account" in action_ids


def test_action_items_for_missing_documents():
    items = generate_action_items(
        scheme_id="pm-kisan",
        missing_fields=[],
        missing_documents=["aadhaar_card", "land_records"],
        language="en",
    )
    action_ids = [i["action_id"] for i in items]
    assert "doc_aadhaar_card" in action_ids
    assert "doc_land_records" in action_ids


def test_no_missing_returns_empty():
    items = generate_action_items(
        scheme_id="pm-kisan",
        missing_fields=[],
        missing_documents=[],
        language="en",
    )
    assert items == []


def test_action_items_have_required_keys():
    items = generate_action_items(
        scheme_id="pm-kisan",
        missing_fields=["aadhaar_number"],
        missing_documents=["aadhaar_card"],
        language="en",
    )
    for item in items:
        assert "action_id" in item
        assert "title" in item
        assert "description" in item
        assert "priority" in item
        assert "category" in item
        assert "scheme_id" in item
