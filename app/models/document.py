from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class OCRBlock(BaseModel):
    text: str
    confidence: float = Field(ge=0, le=1)
    bbox: List[List[float]]
    engine: str


class OCRResult(BaseModel):
    text: str
    confidence: float = Field(ge=0, le=1)
    engine_used: str
    blocks: List[OCRBlock] = []
    doc_type: Optional[str] = None
    structured_fields: Dict = {}
    validated_fields: Dict = {}
    success: bool = True


class DocumentClassification(BaseModel):
    document_type: str  # REJECTION_NOTICE, APPROVAL_LETTER, APPLICATION_FORM
    scheme_id: str
    confidence: float = Field(ge=0, le=1)
    all_scores: Dict = {}


class ScoreComponents(BaseModel):
    fields: int = Field(ge=0, le=60)
    documents: int = Field(ge=0, le=30)
    validation: int = Field(ge=0, le=10)
    fields_detail: str
    docs_detail: str


class ReadinessScore(BaseModel):
    score: int = Field(ge=0, le=100)
    risk_level: str  # LOW, MEDIUM, HIGH
    components: ScoreComponents
    missing_fields: List[str] = []
    missing_documents: List[str] = []
    found_fields: Dict = {}


class DocumentUploadResponse(BaseModel):
    success: bool
    data: Dict


class DocumentResponse(BaseModel):
    document_id: str
    status: str
    language: str
    filename: Optional[str] = None
    ocr_result: Optional[OCRResult] = None
    classification: Optional[DocumentClassification] = None
    score_result: Optional[ReadinessScore] = None
    quality: Optional[Dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None