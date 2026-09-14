"""
Pydantic schemas matching the frontend API contract exactly.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator


# ---------- Survey ----------

class SurveyResponseCreate(BaseModel):
    business_type: Optional[str] = Field(None, max_length=100)
    customer_channels: List[str] = Field(default_factory=list)
    biggest_challenge: Optional[str] = Field(None, max_length=200)
    time_consuming_task: Optional[str] = Field(None, max_length=200)
    order_management: Optional[str] = Field(None, max_length=200)
    payment_tracking: Optional[str] = Field(None, max_length=200)
    technology_used: List[str] = Field(default_factory=list)
    digital_barriers: List[str] = Field(default_factory=list)
    desired_improvement: Optional[str] = Field(None, max_length=2000)
    contact_permission: bool = False
    contact: Optional[str] = Field(None, max_length=255)

    @field_validator("customer_channels", "technology_used", "digital_barriers", mode="before")
    @classmethod
    def ensure_list(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("must be an array")
        # Trim and drop empty strings
        return [str(item).strip() for item in v if str(item).strip()]

    @field_validator(
        "business_type",
        "biggest_challenge",
        "time_consuming_task",
        "order_management",
        "payment_tracking",
        "desired_improvement",
        "contact",
        mode="before",
    )
    @classmethod
    def strip_strings(cls, v):
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    @model_validator(mode="after")
    def clear_contact_if_no_permission(self):
        if not self.contact_permission:
            self.contact = None
        return self


class SurveyResponseOut(BaseModel):
    id: str  # public response_code e.g. BP-2026-000001
    created_at: datetime
    business_type: Optional[str] = None
    customer_channels: List[str] = Field(default_factory=list)
    biggest_challenge: Optional[str] = None
    time_consuming_task: Optional[str] = None
    order_management: Optional[str] = None
    payment_tracking: Optional[str] = None
    technology_used: List[str] = Field(default_factory=list)
    digital_barriers: List[str] = Field(default_factory=list)
    desired_improvement: Optional[str] = None
    contact_permission: bool = False
    contact: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------- Admin auth ----------

class AdminLoginRequest(BaseModel):
    password: str = Field(..., min_length=1, max_length=200)
    model_config = {"extra": "forbid"}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminMeResponse(BaseModel):
    username: str


class MessageResponse(BaseModel):
    message: str


# ---------- Admin list ----------

class ResponseList(BaseModel):
    items: List[SurveyResponseOut]


# ---------- Insights ----------

class BreakdownItem(BaseModel):
    label: str
    count: int
    pct: int


class InsightsResponse(BaseModel):
    total: int
    responses_today: int
    businesses_represented: int
    contact_opt_ins: int
    top_challenges: List[BreakdownItem]
    top_channels: List[BreakdownItem]
    top_time_consuming: List[BreakdownItem]
    top_barriers: List[BreakdownItem]


# ---------- Health ----------

class HealthResponse(BaseModel):
    status: str
