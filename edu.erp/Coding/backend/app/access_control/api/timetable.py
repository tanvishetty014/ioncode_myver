from fastapi import APIRouter, Depends, HTTPException, status
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

# 2. RESET TIMETABLE DATES (Amended to match Service Logic)
@router.patch("/{sem_time_table_id}/reset-dates")
def reset_timetable(sem_time_table_id: int, db: Session = Depends(get_db)):
    # This calls the logic to clear specific date entries from the calendar
    success = timetable_service.reset_timetable_dates_logic(db, sem_time_table_id)
    if not success:
        raise HTTPException(status_code=404, detail="Timetable ID not found")
    return {"message": "Timetable dates reset successfully"}

# 3. COPY CLASS DAY
@router.post("/copy-day")
def copy_day(source_date: date, target_date: date, section: str, db: Session = Depends(get_db)):
    count = timetable_service.copy_class_day_logic(db, source_date, target_date, section)
    return {"message": f"Successfully copied {count} classes to {target_date}"}

# 4. SYNC DATES (ADD/DELETE BASED ON RANGE - Amended function name)
@router.patch("/{sem_time_table_id}/sync-range")
def sync_dates(sem_time_table_id: int, end_date: date, db: Session = Depends(get_db)):
    # This deletes classes that fall outside the new end_date
    deleted_count = timetable_service.sync_timetable_dates_logic(db, sem_time_table_id, end_date)
    return {"message": f"Sync complete. {deleted_count} classes removed beyond the new date range."}