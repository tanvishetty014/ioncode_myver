from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ...db import models
from app.access_control.schemas.curriculum_schemas import (
    SectionOut, TimeTableOut, ScheduledClassOut, ScheduledClassUpdate
)
from ...core.database import get_db

router = APIRouter(prefix="/timetable", tags=["Curriculum & Scheduling"])





# List Available Timetable (Start/End Date & Time)
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
# Scheduled-classes endpoints moved to `scheduled_classes.py` to keep timetabling routes modular.
