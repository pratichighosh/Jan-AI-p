import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import structlog
from uuid import uuid4

from app.models.decision import ActionItem, ActionStep, DeadlineInfo, DecisionOutput

log = structlog.get_logger()

# Field guidance for action items (expandable)
FIELD_GUIDANCE = {
    "pm-kisan": {
        "aadhaar_number": {
            "title": "Aadhaar Number",
            "title_hi": "आधार संख्या",
            "description": "Enter your 12-digit Aadhaar number",
            "description_hi": "अपना 12 अंकों का आधार नंबर दर्ज करें",
            "steps": [
                {"step_number": 1, "description": "Find your Aadhaar card", "description_hi": "अपना आधार कार्ड खोजें"},
                {"step_number": 2, "description": "Enter the 12-digit number", "description_hi": "12 अंकों की संख्या दर्ज करें"},
                {"step_number": 3, "description": "Format: XXXX XXXX XXXX", "description_hi": "प्रारूप: XXXX XXXX XXXX"}
            ]
        },
        "bank_account": {
            "title": "Bank Account Number",
            "title_hi": "बैंक खाता संख्या",
            "description": "Enter your bank account number for direct benefit transfer",
            "description_hi": "सीधे लाभ हस्तांतरण के लिए अपना बैंक खाता नंबर दर्ज करें",
            "steps": [
                {"step_number": 1, "description": "Check your bank passbook or cheque", "description_hi": "अपनी बैंक पासबुक या चेक देखें"},
                {"step_number": 2, "description": "Enter account number carefully", "description_hi": "खाता संख्या ध्यान से दर्ज करें"}
            ]
        },
        "khasra_number": {
            "title": "Khasra Number",
            "title_hi": "खसरा संख्या",
            "description": "Enter land record number from your land documents",
            "description_hi": "अपने भूमि दस्तावेजों से भूमि रिकॉर्ड संख्या दर्ज करें",
            "steps": [
                {"step_number": 1, "description": "Get land ownership documents", "description_hi": "भूमि स्वामित्व दस्तावेज़ प्राप्त करें"},
                {"step_number": 2, "description": "Find khasra number on documents", "description_hi": "दस्तावेजों पर खसरा नंबर खोजें"}
            ]
        }
    },
    "ayushman-bharat": {
        "aadhaar_number": {
            "title": "Aadhaar Number",
            "title_hi": "आधार संख्या",
            "description": "Enter your 12-digit Aadhaar number for health coverage",
            "description_hi": "स्वास्थ्य कवरेज के लिए अपना 12 अंकों का आधार नंबर दर्ज करें",
            "steps": [
                {"step_number": 1, "description": "Keep Aadhaar card ready", "description_hi": "आधार कार्ड तैयार रखें"},
                {"step_number": 2, "description": "Enter 12-digit number", "description_hi": "12 अंकों की संख्या दर्ज करें"}
            ]
        },
        "family_members": {
            "title": "Family Members Count",
            "title_hi": "परिवार के सदस्यों की संख्या",
            "description": "Enter total family members to be covered",
            "description_hi": "कवर किए जाने वाले कुल परिवार के सदस्यों को दर्ज करें",
            "steps": [
                {"step_number": 1, "description": "Count all family members", "description_hi": "सभी परिवार के सदस्यों को गिनें"},
                {"step_number": 2, "description": "Include dependents", "description_hi": "आश्रितों को शामिल करें"}
            ]
        }
    },
    # Add more schemes as needed
}

DOCUMENT_GUIDANCE = {
    "land_records": {
        "title": "Land Ownership Documents",
        "title_hi": "भूमि स्वामित्व दस्तावेज़",
        "description": "Upload land records showing ownership and khasra number",
        "description_hi": "स्वामित्व और खसरा नंबर दिखाने वाले भूमि रिकॉर्ड अपलोड करें",
        "steps": [
            {"step_number": 1, "description": "Get land records from tehsil office or online portal", "description_hi": "तहसील कार्यालय या ऑनलाइन पोर्टल से भूमि रिकॉर्ड प्राप्त करें"},
            {"step_number": 2, "description": "Scan or photograph clearly", "description_hi": "स्पष्ट रूप से स्कैन या फोटो लें"},
            {"step_number": 3, "description": "Upload PDF or image", "description_hi": "PDF या छवि अपलोड करें"}
        ]
    },
    "aadhaar_card": {
        "title": "Aadhaar Card",
        "title_hi": "आधार कार्ड",
        "description": "Upload clear photo or scan of Aadhaar card",
        "description_hi": "आधार कार्ड की स्पष्ट फोटो या स्कैन अपलोड करें",
        "steps": [
            {"step_number": 1, "description": "Place Aadhaar on flat surface", "description_hi": "आधार को समतल सतह पर रखें"},
            {"step_number": 2, "description": "Take clear photo in good lighting", "description_hi": "अच्छी रोशनी में स्पष्ट फोटो लें"},
            {"step_number": 3, "description": "Upload both front and back if required", "description_hi": "यदि आवश्यक हो तो आगे और पीछे दोनों अपलोड करें"}
        ]
    },
    "bank_passbook": {
        "title": "Bank Passbook",
        "title_hi": "बैंक पासबुक",
        "description": "Upload first page of bank passbook showing account details",
        "description_hi": "खाता विवरण दिखाने वाली बैंक पासबुक का पहला पेज अपलोड करें",
        "steps": [
            {"step_number": 1, "description": "Open first page of passbook", "description_hi": "पासबुक का पहला पेज खोलें"},
            {"step_number": 2, "description": "Ensure account number and IFSC are visible", "description_hi": "सुनिश्चित करें कि खाता संख्या और IFSC दिखाई दें"},
            {"step_number": 3, "description": "Upload clear image", "description_hi": "स्पष्ट छवि अपलोड करें"}
        ]
    },
    "income_certificate": {
        "title": "Income Certificate",
        "title_hi": "आय प्रमाण पत्र",
        "description": "Upload income certificate from competent authority",
        "description_hi": "सक्षम प्राधिकारी से आय प्रमाण पत्र अपलोड करें",
        "steps": [
            {"step_number": 1, "description": "Get income certificate from tehsildar", "description_hi": "तहसीलदार से आय प्रमाण पत्र प्राप्त करें"},
            {"step_number": 2, "description": "Scan the document", "description_hi": "दस्तावेज़ को स्कैन करें"},
            {"step_number": 3, "description": "Upload PDF or image", "description_hi": "PDF या छवि अपलोड करें"}
        ]
    }
}


def extract_deadline(ocr_text: str) -> Optional[DeadlineInfo]:
    """
    Extract deadline information from OCR text.
    Looks for common patterns like:
    - "Last date: DD/MM/YYYY"
    - "अंतिम तिथि: DD/MM/YYYY"
    - "Deadline: DD-MM-YYYY"
    """
    deadline_patterns = [
        r"(?:last date|अंतिम तिथि|deadline)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})",
        r"(?:submit by|before|तक)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})",
        r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})(?:\s+तक|\ before)"
    ]
    
    for pattern in deadline_patterns:
        match = re.search(pattern, ocr_text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            try:
                # Try different date formats
                for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"]:
                    try:
                        deadline_date = datetime.strptime(date_str, fmt)
                        days_remaining = (deadline_date - datetime.now()).days
                        
                        return DeadlineInfo(
                            has_deadline=True,
                            deadline_date=deadline_date,
                            days_remaining=days_remaining,
                            deadline_text=date_str,
                            is_urgent=(days_remaining < 7)
                        )
                    except ValueError:
                        continue
            except Exception as e:
                log.warning("deadline_parse_failed", error=str(e))
                continue
    
    return DeadlineInfo(has_deadline=False)


def calculate_field_priority(
    field_name: str,
    scheme_id: str,
    deadline_info: Optional[DeadlineInfo] = None
) -> int:
    """
    Calculate priority for a missing field (1 = highest, 10 = lowest).
    
    Priority factors:
    - Critical fields (aadhaar, bank account): priority 1-2
    - Required fields: priority 3-5
    - Optional fields: priority 6-10
    - Urgent deadline: -2 priority (higher)
    """
    # Critical fields
    critical_fields = ["aadhaar_number", "pan_number", "bank_account", "applicant_name"]
    if field_name in critical_fields:
        priority = 1
    else:
        priority = 4
    
    # Adjust for deadline urgency
    if deadline_info and deadline_info.is_urgent:
        priority = max(1, priority - 2)
    
    return priority


def generate_field_action_item(
    field_name: str,
    scheme_id: str,
    priority: int,
    deadline_info: Optional[DeadlineInfo] = None
) -> ActionItem:
    """
    Generate action item for a missing field.
    """
    guidance = FIELD_GUIDANCE.get(scheme_id, {}).get(
        field_name,
        {
            "title": field_name.replace("_", " ").title(),
            "title_hi": field_name.replace("_", " "),
            "description": f"Fill in the {field_name.replace('_', ' ')} field",
            "description_hi": f"{field_name.replace('_', ' ')} फ़ील्ड भरें",
            "steps": []
        }
    )
    
    steps = [
        ActionStep(**step) for step in guidance.get("steps", [])
    ]
    
    return ActionItem(
        id=f"field_{uuid4().hex[:8]}",
        title=guidance["title"],
        title_hi=guidance["title_hi"],
        description=guidance["description"],
        description_hi=guidance["description_hi"],
        category="FILL_FIELD",
        priority=priority,
        field_name=field_name,
        steps=steps,
        deadline=deadline_info.deadline_date if deadline_info and deadline_info.has_deadline else None
    )


def generate_document_action_item(
    document_type: str,
    scheme_id: str,
    priority: int,
    deadline_info: Optional[DeadlineInfo] = None
) -> ActionItem:
    """
    Generate action item for a missing document.
    """
    guidance = DOCUMENT_GUIDANCE.get(
        document_type,
        {
            "title": document_type.replace("_", " ").title(),
            "title_hi": document_type.replace("_", " "),
            "description": f"Upload {document_type.replace('_', ' ')}",
            "description_hi": f"{document_type.replace('_', ' ')} अपलोड करें",
            "steps": []
        }
    )
    
    steps = [
        ActionStep(**step) for step in guidance.get("steps", [])
    ]
    
    return ActionItem(
        id=f"doc_{uuid4().hex[:8]}",
        title=guidance["title"],
        title_hi=guidance["title_hi"],
        description=guidance["description"],
        description_hi=guidance["description_hi"],
        category="UPLOAD_DOCUMENT",
        priority=priority + 1,  # Documents slightly lower priority than fields
        document_type=document_type,
        steps=steps,
        deadline=deadline_info.deadline_date if deadline_info and deadline_info.has_deadline else None
    )


def generate_action_items(
    missing_fields: List[str],
    missing_documents: List[str],
    scheme_id: str,
    ocr_text: str
) -> Tuple[List[ActionItem], Optional[DeadlineInfo]]:
    """
    Generate prioritized action items based on missing fields and documents.
    """
    # Extract deadline
    deadline_info = extract_deadline(ocr_text)
    
    action_items = []
    
    # Generate field action items
    for field in missing_fields:
        priority = calculate_field_priority(field, scheme_id, deadline_info)
        action = generate_field_action_item(field, scheme_id, priority, deadline_info)
        action_items.append(action)
    
    # Generate document action items
    for doc in missing_documents:
        priority = calculate_field_priority(doc, scheme_id, deadline_info)
        action = generate_document_action_item(doc, scheme_id, priority, deadline_info)
        action_items.append(action)
    
    # Sort by priority
    action_items.sort(key=lambda x: x.priority)
    
    return action_items, deadline_info


def create_decision_output(
    document_id: str,
    scheme_id: str,
    readiness_score: int,
    risk_level: str,
    missing_fields: List[str],
    missing_documents: List[str],
    ocr_text: str
) -> DecisionOutput:
    """
    Create complete decision output with action items.
    """
    # Generate action items
    action_items, deadline_info = generate_action_items(
        missing_fields, missing_documents, scheme_id, ocr_text
    )
    
    # Create summary
    total_actions = len(action_items)
    if total_actions == 0:
        summary = "Your application appears complete. Review and submit."
        summary_hi = "आपका आवेदन पूर्ण दिखाई देता है। समीक्षा करें और जमा करें।"
    else:
        summary = f"Complete {total_actions} action items to improve your application readiness."
        summary_hi = f"अपने आवेदन की तैयारी में सुधार के लिए {total_actions} कार्य आइटम पूरे करें।"
    
    # Estimate completion time
    estimated_time = f"{total_actions * 5} minutes" if total_actions > 0 else "0 minutes"
    
    # Scheme name mapping
    scheme_names = {
        "pm-kisan": {"en": "PM-KISAN", "hi": "पीएम किसान"},
        "ayushman-bharat": {"en": "Ayushman Bharat", "hi": "आयुष्मान भारत"},
        "ration-card": {"en": "Ration Card", "hi": "राशन कार्ड"},
        "aadhaar-services": {"en": "Aadhaar Services", "hi": "आधार सेवाएं"},
        "social-pension": {"en": "Social Pension", "hi": "सामाजिक पेंशन"},
        "pan-card": {"en": "PAN Card", "hi": "पैन कार्ड"},
    }
    
    scheme_info = scheme_names.get(scheme_id, {"en": scheme_id, "hi": scheme_id})
    
    return DecisionOutput(
        document_id=document_id,
        scheme_id=scheme_id,
        scheme_name=scheme_info["en"],
        scheme_name_hi=scheme_info["hi"],
        readiness_score=readiness_score,
        risk_level=risk_level,
        action_items=action_items,
        deadline_info=deadline_info,
        next_steps_summary=summary,
        next_steps_summary_hi=summary_hi,
        estimated_completion_time=estimated_time
    )