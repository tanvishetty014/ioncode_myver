from fastapi import APIRouter, Depends, HTTPException, status, Query  # Added Query here
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from ...db import models
from app.access_control.schemas.curriculum_schemas import (
    SectionOut, TimeTableOut, ScheduledClassOut, ScheduledClassUpdate
)
from ...core.database import get_db
# Import the service logic
from ..services import timetable_service 

router = APIRouter(prefix="/timetable", tags=["Curriculum & Scheduling"])

# --- EXISTING CODE ---

@router.get("/timetables", response_model=List[TimeTableOut])
def get_timetables(term: str, section: str, db: Session = Depends(get_db)):
    results = db.query(
        models.IEMSTimeTable.time_table_id,
        models.IEMSTimeTable.crs_code,
        models.IEMSTimeTable.start_time,
        models.IEMSTimeTable.end_time,
        models.IEMSemTimeTable.section,
        models.IEMSemTimeTable.term
    ).join(
        models.IEMSemTimeTable,
        models.IEMSemTimeTable.id == models.IEMSTimeTable.sem_time_table_id
    ).filter(
        models.IEMSemTimeTable.term == term,
        models.IEMSemTimeTable.section == section
    ).all()

    return [
        {
            "time_table_id": row[0],
            "crs_code": row[1],
            "start_time": row[2],
            "end_time": row[3],
            "section": row[4],
            "term": row[5]
        }
        for row in results
    ]

# --- NEW TASKS AMENDED ---

# 1. DELETE TIMETABLE
@router.delete("/{sem_time_table_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_timetable(sem_time_table_id: int, db: Session = Depends(get_db)):
    success = timetable_service.delete_timetable_logic(db, sem_time_table_id)
    if not success:
        raise HTTPException(status_code=404, detail="Timetable not found")
    return None

# 2. RESET TIMETABLE DATES
@router.patch("/{sem_time_table_id}/reset-dates")
def reset_timetable(sem_time_table_id: int, db: Session = Depends(get_db)):
    success = timetable_service.reset_timetable_dates_logic(db, sem_time_table_id)
    if not success:
        raise HTTPException(status_code=404, detail="Timetable ID not found")
    return {"message": "Timetable dates reset successfully"}

# 3. COPY CLASS DAY (UPDATED WITH FRIEND'S FIXES)
@router.post("/copy-day")
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
@router.patch("/{sem_time_table_id}/sync-range")
def sync_dates(
    sem_time_table_id: int, 
    end_date: date = Query(...), # Added Query here as well for consistency
    db: Session = Depends(get_db)
):
    deleted_count = timetable_service.sync_timetable_dates_logic(db, sem_time_table_id, end_date)
    return {"message": f"Sync complete. {deleted_count} classes removed beyond the new date range."}


# --- New endpoints requested ---
@router.get("/created-dates", response_model=List[date])
def get_created_dates(crs_code: str = Query(..., description="Course code"), db: Session = Depends(get_db)):
    """Return list of distinct creation dates for timetable entries for a given course."""
    dates = timetable_service.get_timetable_created_dates_for_course(db, crs_code)
    return dates


@router.get("/has-lesson")
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