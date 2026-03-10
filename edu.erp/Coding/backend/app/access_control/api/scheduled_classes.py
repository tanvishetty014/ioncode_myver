from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ...db import models
from app.access_control.schemas.curriculum_schemas import (
    ScheduledClassOut, ScheduledClassUpdate
)
from ...core.database import get_db

router = APIRouter(prefix="/timetable", tags=["Curriculum & Scheduling"])


# --- 5. List Scheduled Classes API ---
@router.get("/scheduled-classes", response_model=List[ScheduledClassOut])
def list_scheduled_classes(
    section: Optional[str] = None,
    date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.IEMSCustomTimeTable)
    if section:
        query = query.filter(models.IEMSCustomTimeTable.section == section)
    if date:
        query = query.filter(models.IEMSCustomTimeTable.date == date)
    return query.all()


# --- 6. Edit Scheduled Class API ---
@router.put("/scheduled-classes/{class_id}", response_model=ScheduledClassOut)
def edit_scheduled_class(
    class_id: int,
    class_update: ScheduledClassUpdate,
    db: Session = Depends(get_db)
):
    db_class = db.query(models.IEMSCustomTimeTable).filter(
        models.IEMSCustomTimeTable.id == class_id
    ).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Scheduled class not found")

    # Support both Pydantic v1 (`.dict`) and v2 (`.model_dump`)
    if hasattr(class_update, "model_dump"):
        update_data = class_update.model_dump(exclude_unset=True)
    else:
        update_data = class_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_class, key, value)

    db.commit()
    db.refresh(db_class)
    return db_class


# --- 7. Delete Scheduled Class API ---
@router.delete("/scheduled-classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheduled_class(class_id: int, db: Session = Depends(get_db)):
    db_class = db.query(models.IEMSCustomTimeTable).filter(
        models.IEMSCustomTimeTable.id == class_id
    ).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Scheduled class not found")

    db.delete(db_class)
    db.commit()
    return None
