from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

# Internal Schemas
from app.access_control.schemas.attendance import (
    AttendanceSavePayload,
    AttendanceSummaryResponse,
    LessonDatesResponse,
)

# Database and Services
from ...db import models
from ...core.database import get_db
from ..services import timetable_service
from app.api.v1.ems_module.comman_functions.comman_function import get_students

router = APIRouter(tags=["Attendance"])

# ─── UTILITIES ───────────────────────────────────────────────────────────────

def _ensure_required_params(params: dict) -> None:
    """Helper to ensure all required query parameters are present."""
    missing = [key for key, value in params.items() if value is None]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required query params: {', '.join(missing)}",
        )

# ─── ENDPOINTS ───────────────────────────────────────────────────────────────

@router.get("/attendance/fetch")
def fetch_attendance(
    crs_code: str = Query(...),
    day: date = Query(...),
    start_time: str = Query(...),
    end_time: str = Query(...),
    section: Optional[str] = Query(None),
    sem_time_table_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Fetch student attendance records for the selected class timing."""
    rows = timetable_service.get_attendance_for_timing(
        db, crs_code, day, start_time, end_time, section, sem_time_table_id
    )
    if not rows:
        return {"message": "No attendance records found", "attendance": []}
    return {"attendance": rows}


@router.post("/attendance/save")
def save_attendance(payload: AttendanceSavePayload, db: Session = Depends(get_db)):
    """Save attendance data (batch upsert). Provide `meta` with class context and `records` list."""
    meta = payload.meta
    required = ["crs_code", "result_year", "start_time", "end_time"]
    
    for r in required:
        if r not in meta:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Missing meta field: {r}"
            )

    # Convert result_year to date if it's a string
    if isinstance(meta.get("result_year"), str):
        try:
            from datetime import datetime as _dt
            meta["result_year"] = _dt.fromisoformat(meta["result_year"]).date()
        except Exception:
            raise HTTPException(
                status_code=400, 
                detail="Invalid result_year format. Use YYYY-MM-DD."
            )

    attendance_list = [r.model_dump() for r in payload.records]
    result = timetable_service.save_attendance_batch(db, attendance_list, meta)
    return {"message": "Attendance saved", "result": result}


@router.get("/attendance/lesson-dates", response_model=LessonDatesResponse)
def get_lesson_dates(
    academic_batch_id: Optional[int] = Query(None),
    semester_id: Optional[int] = Query(None),
    course_id: Optional[int] = Query(None),
    section_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Retrieve all dates where lessons were scheduled for a specific course/section."""
    _ensure_required_params({
        "academic_batch_id": academic_batch_id,
        "semester_id": semester_id,
        "course_id": course_id,
        "section_id": section_id,
    })
    
    dates = timetable_service.get_attendance_lesson_dates(
        db=db,
        academic_batch_id=academic_batch_id,
        semester_id=semester_id,
        course_id=course_id,
        section_id=section_id,
    )
    return {"dates": dates}


@router.get("/attendance/summary", response_model=AttendanceSummaryResponse)
def get_attendance_summary(
    academic_batch_id: Optional[int] = Query(None),
    semester_id: Optional[int] = Query(None),
    course_id: Optional[int] = Query(None),
    section_id: Optional[int] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    only_present: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Get summarized attendance percentages for students in a specific range."""
    # 1. Date Validation
    if from_date and to_date and from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="from_date cannot be greater than to_date",
        )

    try:
        # 2. Call service logic
        students = timetable_service.get_attendance_summary(
            db=db,
            academic_batch_id=academic_batch_id,
            semester_id=semester_id,
            course_id=course_id,
            section_id=section_id,
            from_date=from_date,
            to_date=to_date,
            only_present=only_present,
        )

        # 3. Safe check: return empty list if None to prevent React map() errors
        if students is None:
            return {"students": []}
            
        return {"students": students}

    except Exception as e:
        # 4. Log the error to the terminal for debugging
        print(f"DEBUG: Error in attendance summary: {str(e)}")
        # 5. Fallback: Return empty data instead of a 500 error
        return {"students": []}

# ─── EXTRA ROUTES ────────────────────────────────────────────────────────────

# Route for student dropdowns in the attendance module
router.add_api_route("/comman_function/students", get_students, methods=["GET"])