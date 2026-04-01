from fastapi import APIRouter, Depends, HTTPException, status, Query  # Added Query here
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from ...db import models
from app.access_control.schemas.curriculum_schemas import (
    SectionOut, TimeTableOut, ScheduledClassOut, ScheduledClassUpdate
)
from ...core.database import get_db
# Import the service logic
from ..services import timetable_service 
from app.api.v1.ems_module.comman_functions.comman_function import (
    export_timetable_pdf,
    get_timetable_data,
    get_timetable,
)

router = APIRouter(tags=["Curriculum & Scheduling"])


def _success_response(data, message: str = "Data fetched successfully", status_code: int = status.HTTP_200_OK):
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status_code,
            "message": message,
            "data": jsonable_encoder(data),
        },
    )


def _error_response(message: str, error: str, status_code: int = status.HTTP_400_BAD_REQUEST):
    return JSONResponse(
        status_code=status_code,
        content={
            "status": status_code,
            "message": message,
            "error": error,
        },
    )

# --- EXISTING CODE ---

@router.get("/timetable/timetables")
def get_timetables(term: int, section: int, db: Session = Depends(get_db)):
    section_row = db.query(models.IEMSection).filter(
        models.IEMSection.id == section,
        models.IEMSection.semester_id == term
    ).first()

    if not section_row:
        return _error_response(
            message="Invalid input",
            error="Section not found for the provided crclm_term_id"
        )

    term_row = db.query(models.IEMSCrclmTerm).filter(
        models.IEMSCrclmTerm.crclm_term_id == term
    ).first()

    if not term_row:
        return _error_response(
            message="Invalid input",
            error="crclm_term_id not found"
        )

    semester_row = db.query(models.IEMSemester).filter(
        models.IEMSemester.academic_batch_id == section_row.academic_batch_id,
        models.IEMSemester.semester == term_row.term_name,
        models.IEMSemester.status == 1,
    ).order_by(models.IEMSemester.semester_id.asc()).first()

    if not semester_row:
        return _error_response(
            message="Invalid input",
            error="No valid semester found for the provided crclm_term_id"
        )

    timetable_rows = get_timetable_data(
        academic_batch_id=section_row.academic_batch_id,
        semester_id=semester_row.semester_id,
        section_id=section_row.id,
        db=db,
    )

    data = [{
        "schedule_id": row["schedule_id"],
        "subject": row["crs_title"] or row["crs_code"],
        "faculty": row["faculty_name"] or "Not Assigned",
        "date": row["plan_date"],
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "crs_id": row["crs_id"],
        "section_id": section_row.id,
        "section_name": section_row.section,
        "academic_batch_id": section_row.academic_batch_id,
        "semester_id": semester_row.semester_id,
        "crclm_term_id": term_row.crclm_term_id,
    } for row in timetable_rows]
    return _success_response(data)

# --- NEW TASKS AMENDED ---

# 1. DELETE TIMETABLE
@router.delete("/timetable/{sem_time_table_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_timetable(sem_time_table_id: int, db: Session = Depends(get_db)):
    success = timetable_service.delete_timetable_logic(db, sem_time_table_id)
    if not success:
        raise HTTPException(status_code=404, detail="Timetable not found")
    return None

# 2. RESET TIMETABLE DATES
@router.patch("/timetable/{sem_time_table_id}/reset-dates")
def reset_timetable(sem_time_table_id: int, db: Session = Depends(get_db)):
    success = timetable_service.reset_timetable_dates_logic(db, sem_time_table_id)
    if not success:
        raise HTTPException(status_code=404, detail="Timetable ID not found")
    return {"message": "Timetable dates reset successfully"}

# 3. COPY CLASS DAY (UPDATED WITH FRIEND'S FIXES)
@router.post("/timetable/copy-day")
def copy_day(
    source_date: date = Query(...), 
    target_date: date = Query(...), 
    section: str = Query(...), 
    db: Session = Depends(get_db)
):
    # Call the service logic
    count = timetable_service.copy_class_day_logic(db, source_date, target_date, section)
    
    # Logic Fix: If count is 0, it means nothing was found to copy. 
    # Instead of a success message, we throw a 404 error.
    if count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"No classes found for section {section} on {source_date} to copy."
        )
        
    return {"message": f"Successfully copied {count} classes to {target_date}"}

# 4. SYNC DATES
@router.patch("/timetable/{sem_time_table_id}/sync-range")
def sync_dates(
    sem_time_table_id: int, 
    end_date: date = Query(...), # Added Query here as well for consistency
    db: Session = Depends(get_db)
):
    deleted_count = timetable_service.sync_timetable_dates_logic(db, sem_time_table_id, end_date)
    return {"message": f"Sync complete. {deleted_count} classes removed beyond the new date range."}


# --- New endpoints requested ---
@router.get("/timetable/created-dates")
def get_created_dates(crs_code: str = Query(..., description="Course code"), db: Session = Depends(get_db)):
    """Return list of distinct creation dates for timetable entries for a given course."""
    dates = timetable_service.get_timetable_created_dates_for_course(db, crs_code)
    return _success_response(dates)


@router.get("/timetable/has-lesson")
def has_lesson(crs_code: str = Query(..., description="Course code"),
               day: date = Query(..., description="Date to check (YYYY-MM-DD)"),
               section: Optional[str] = Query(None, description="Optional section filter"),
               db: Session = Depends(get_db)):
    """Check if any lesson is scheduled for the given course on the specified date.

    Returns `{ 'scheduled': True|False }`.
    """
    # First check existence to avoid unnecessary timing queries when none exist
    exists = timetable_service.is_lesson_scheduled_on_date(db, crs_code, day, section)
    if not exists:
        return {"message": "No classes scheduled"}

    timings = timetable_service.get_scheduled_class_timings(db, crs_code, day, section)
    return {"scheduled": True, "timings": timings}


# router.add_api_route("/comman_function/timetable", get_timetable, methods=["GET"])
router.add_api_route(
    "/timetable/export-pdf",
    export_timetable_pdf,
    methods=["GET"],
    include_in_schema=True,
)
