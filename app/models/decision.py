from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class ActionStep(BaseModel):
    step_number: int
    description: str
    description_hi: str
    estimated_time: Optional[str] = None  # e.g., "5 minutes", "1 hour"


class ActionItem(BaseModel):
    id: str
    title: str
    title_hi: str
    description: str
    description_hi: str
    category: str  # FILL_FIELD, UPLOAD_DOCUMENT, CORRECT_ERROR, VISIT_OFFICE
    priority: int = Field(ge=1, le=10)  # 1 = highest priority
    field_name: Optional[str] = None
    document_type: Optional[str] = None
    steps: List[ActionStep] = []
    completed: bool = False
    deadline: Optional[datetime] = None


class DeadlineInfo(BaseModel):
    has_deadline: bool
    deadline_date: Optional[datetime] = None
    days_remaining: Optional[int] = None
    deadline_text: Optional[str] = None
    is_urgent: bool = False  # < 7 days


class DecisionOutput(BaseModel):
    document_id: str
    scheme_id: str
    scheme_name: str
    scheme_name_hi: str
    readiness_score: int = Field(ge=0, le=100)
    risk_level: str  # LOW, MEDIUM, HIGH
    action_items: List[ActionItem] = []
    deadline_info: Optional[DeadlineInfo] = None
    next_steps_summary: str
    next_steps_summary_hi: str
    estimated_completion_time: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProgressUpdate(BaseModel):
    document_id: str
    action_id: str
    completed: bool
    completion_note: Optional[str] = None