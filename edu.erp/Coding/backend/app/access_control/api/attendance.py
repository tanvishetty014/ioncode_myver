from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.access_control.schemas.attendance import AttendanceSavePayload

from ...db import models
from ...core.database import get_db
from ..services import timetable_service

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("/fetch")
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
    rows = timetable_service.get_attendance_for_timing(db, crs_code, day, start_time, end_time, section, sem_time_table_id)
    if not rows:
        return {"message": "No attendance records found"}
    return {"attendance": rows}


@router.post("/save")
def save_attendance(payload: AttendanceSavePayload, db: Session = Depends(get_db)):
    """Save attendance data (batch upsert). Provide `meta` with class context and `records` list."""
    # Validate meta required fields
    meta = payload.meta
    required = ["crs_code", "result_year", "start_time", "end_time"]
    for r in required:
        if r not in meta:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing meta field: {r}")

    # Convert result_year to date if it's a string
    if isinstance(meta.get("result_year"), str):
        try:
            from datetime import datetime as _dt
            meta["result_year"] = _dt.fromisoformat(meta["result_year"]).date()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid result_year format. Use YYYY-MM-DD.")

    attendance_list = [r.model_dump() for r in payload.records]
    result = timetable_service.save_attendance_batch(db, attendance_list, meta)
    return {"message": "Attendance saved", "result": result}
