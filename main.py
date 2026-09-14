"""
IGRIS Business Pulse API
FastAPI backend matching the existing frontend contract.
"""
import csv
import io
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from auth import (
    create_access_token,
    get_current_admin,
    hash_password,
    verify_password,
)
from database import Base, engine, get_db, get_settings
from models import AdminUser, Response
from schemas import (
    AdminLoginRequest,
    AdminMeResponse,
    HealthResponse,
    InsightsResponse,
    BreakdownItem,
    MessageResponse,
    ResponseList,
    SurveyResponseCreate,
    SurveyResponseOut,
    TokenResponse,
)

settings = get_settings()

app = FastAPI(
    title="IGRIS Business Pulse API",
    description="Research survey backend for IGRIS Technologies. Matches the existing frontend contract.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow any frontend origin during development and cross-origin testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# ---------- Startup ----------

@app.on_event("startup")
def on_startup():
    """Create tables and ensure a default admin exists."""
    Base.metadata.create_all(bind=engine)

    db = next(get_db())
    try:
        admin = db.query(AdminUser).filter(AdminUser.username == settings.ADMIN_USERNAME).first()
        if not admin:
            admin = AdminUser(
                username=settings.ADMIN_USERNAME,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


# ---------- Helpers ----------

def _next_response_code(db: Session) -> str:
    """Generate BP-YYYY-NNNNNN sequential public response codes."""
    year = datetime.now(timezone.utc).year
    prefix = f"BP-{year}-"
    # Find the highest existing sequence for this year
    latest = (
        db.query(Response.response_code)
        .filter(Response.response_code.like(f"{prefix}%"))
        .order_by(Response.response_code.desc())
        .first()
    )
    if latest:
        try:
            seq = int(latest[0].split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:06d}"


def _to_out(row: Response) -> SurveyResponseOut:
    return SurveyResponseOut(
        id=row.response_code,
        created_at=row.created_at,
        business_type=row.business_type,
        customer_channels=row.customer_channels or [],
        biggest_challenge=row.biggest_challenge,
        time_consuming_task=row.time_consuming_task,
        order_management=row.order_management,
        payment_tracking=row.payment_tracking,
        technology_used=row.technology_used or [],
        digital_barriers=row.digital_barriers or [],
        desired_improvement=row.desired_improvement,
        contact_permission=row.contact_permission,
        contact=row.contact,
    )


def _percentage_breakdown(values: list, total: int, limit: int = 10) -> list[BreakdownItem]:
    if not values or total == 0:
        return []
    counts = Counter(v for v in values if v)
    items = []
    for label, count in counts.most_common(limit):
        pct = round((count / total) * 100) if total else 0
        items.append(BreakdownItem(label=label, count=count, pct=pct))
    return items


# ---------- Health ----------

@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
def health():
    """Liveness check for hosting platforms."""
    return HealthResponse(status="ok")


# ---------- Survey ----------

@app.post(
    "/api/v1/survey/responses",
    response_model=SurveyResponseOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Survey"],
)
def create_survey_response(payload: SurveyResponseCreate, db: Session = Depends(get_db)):
    """
    Accept a completed survey response.
    Returns the stored record with a public response code (e.g. BP-2026-000001).
    """
    code = _next_response_code(db)

    row = Response(
        response_code=code,
        business_type=payload.business_type,
        customer_channels=payload.customer_channels,
        biggest_challenge=payload.biggest_challenge,
        time_consuming_task=payload.time_consuming_task,
        order_management=payload.order_management,
        payment_tracking=payload.payment_tracking,
        technology_used=payload.technology_used,
        digital_barriers=payload.digital_barriers,
        desired_improvement=payload.desired_improvement,
        contact_permission=payload.contact_permission,
        contact=payload.contact if payload.contact_permission else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


# ---------- Admin auth ----------

@app.post("/api/v1/admin/login", response_model=TokenResponse, tags=["Admin Auth"])
def admin_login(body: AdminLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate admin with password.
    Returns a JWT bearer token.
    """
    admin = db.query(AdminUser).filter(AdminUser.username == settings.ADMIN_USERNAME).first()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )

    admin.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(subject=admin.username)
    return TokenResponse(access_token=token, token_type="bearer")


@app.get("/api/v1/admin/me", response_model=AdminMeResponse, tags=["Admin Auth"])
def admin_me(admin: AdminUser = Depends(get_current_admin)):
    """Confirm the current JWT is valid and return the admin username."""
    return AdminMeResponse(username=admin.username)


@app.post("/api/v1/admin/logout", response_model=MessageResponse, tags=["Admin Auth"])
def admin_logout(admin: AdminUser = Depends(get_current_admin)):
    """
    Logout endpoint.
    JWTs are stateless — the frontend should discard its local token.
    This endpoint simply confirms the token was valid.
    """
    return MessageResponse(message="Logged out")


# ---------- Admin responses ----------

@app.get("/api/v1/admin/responses", response_model=ResponseList, tags=["Admin"])
def list_responses(
    business_type: Optional[str] = Query(None),
    challenge: Optional[str] = Query(None),
    contact_opt_in: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    List survey responses with optional filters.
    Authenticated. Default limit 50, max 200.
    """
    q = db.query(Response)

    if business_type:
        q = q.filter(Response.business_type == business_type)
    if challenge:
        q = q.filter(Response.biggest_challenge == challenge)
    if contact_opt_in is not None:
        q = q.filter(Response.contact_permission == contact_opt_in)
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                Response.business_type.ilike(term),
                Response.biggest_challenge.ilike(term),
                Response.time_consuming_task.ilike(term),
                Response.order_management.ilike(term),
                Response.payment_tracking.ilike(term),
                Response.desired_improvement.ilike(term),
                Response.contact.ilike(term),
                Response.response_code.ilike(term),
            )
        )

    rows = (
        q.order_by(Response.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return ResponseList(items=[_to_out(r) for r in rows])


@app.get(
    "/api/v1/admin/responses/{response_id}",
    response_model=SurveyResponseOut,
    tags=["Admin"],
)
def get_response(
    response_id: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Fetch a single response by its public code (e.g. BP-2026-000001)."""
    row = db.query(Response).filter(Response.response_code == response_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Response not found")
    return _to_out(row)


# ---------- Insights ----------

@app.get("/api/v1/admin/insights", response_model=InsightsResponse, tags=["Admin"])
def get_insights(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    Aggregated research insights from real stored responses.
    Returns zeros and empty lists when the database is empty.
    """
    total = db.query(func.count(Response.id)).scalar() or 0

    if total == 0:
        return InsightsResponse(
            total=0,
            responses_today=0,
            businesses_represented=0,
            contact_opt_ins=0,
            top_challenges=[],
            top_channels=[],
            top_time_consuming=[],
            top_barriers=[],
        )

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    responses_today = (
        db.query(func.count(Response.id))
        .filter(Response.created_at >= today_start)
        .scalar()
        or 0
    )

    businesses_represented = (
        db.query(func.count(func.distinct(Response.business_type)))
        .filter(Response.business_type.isnot(None))
        .scalar()
        or 0
    )

    contact_opt_ins = (
        db.query(func.count(Response.id))
        .filter(Response.contact_permission.is_(True))
        .scalar()
        or 0
    )

    # Pull values for breakdowns (simple approach for this scale)
    all_rows = db.query(
        Response.biggest_challenge,
        Response.customer_channels,
        Response.time_consuming_task,
        Response.digital_barriers,
    ).all()

    challenges = [r.biggest_challenge for r in all_rows if r.biggest_challenge]
    time_tasks = [r.time_consuming_task for r in all_rows if r.time_consuming_task]

    # Flatten array fields
    channels = []
    barriers = []
    for r in all_rows:
        if r.customer_channels:
            channels.extend(r.customer_channels)
        if r.digital_barriers:
            barriers.extend(r.digital_barriers)

    return InsightsResponse(
        total=total,
        responses_today=responses_today,
        businesses_represented=businesses_represented,
        contact_opt_ins=contact_opt_ins,
        top_challenges=_percentage_breakdown(challenges, total),
        top_channels=_percentage_breakdown(channels, total),
        top_time_consuming=_percentage_breakdown(time_tasks, total),
        top_barriers=_percentage_breakdown(barriers, total),
    )


# ---------- Export ----------

@app.get("/api/v1/admin/export", tags=["Admin"])
def export_csv(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """
    Export all responses as CSV.
    Content-Type: text/csv
    """
    rows = db.query(Response).order_by(Response.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "id",
        "created_at",
        "business_type",
        "customer_channels",
        "biggest_challenge",
        "time_consuming_task",
        "order_management",
        "payment_tracking",
        "technology_used",
        "digital_barriers",
        "desired_improvement",
        "contact_permission",
        "contact",
    ]
    writer.writerow(headers)

    for r in rows:
        writer.writerow(
            [
                r.response_code,
                r.created_at.isoformat() if r.created_at else "",
                r.business_type or "",
                "|".join(r.customer_channels or []),
                r.biggest_challenge or "",
                r.time_consuming_task or "",
                r.order_management or "",
                r.payment_tracking or "",
                "|".join(r.technology_used or []),
                "|".join(r.digital_barriers or []),
                r.desired_improvement or "",
                "Yes" if r.contact_permission else "No",
                r.contact or "",
            ]
        )

    output.seek(0)
    filename = f"igris-business-pulse-responses-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
