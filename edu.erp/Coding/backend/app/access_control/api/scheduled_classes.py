from datetime import timedelta, time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from ...db import models
from app.access_control.schemas.curriculum_schemas import (
    ScheduledClassOut, ScheduledClassUpdate
)
from ...core.database import get_db
from app.api.v1.ems_module.comman_functions.comman_function import (
    add_extra_class,
    check_duplicate,
    get_scheduled_classes,
    get_topic_lessons,
    save_schedule,
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


def _format_time_value(value):
    if value is None:
        return None

    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"

    if isinstance(value, time):
        return value.strftime("%H:%M")

    value_str = str(value).strip()
    if len(value_str) >= 5 and ":" in value_str:
        parts = value_str.split(":")
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"

    return value_str


def _scheduled_classes_array(
    section: Optional[str] = None,
    date: Optional[str] = None,
    academic_batch_id: Optional[int] = None,
    semester_id: Optional[int] = None,
    course_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.LMSLessonSchedule)
    if section:
        section_row = db.query(models.IEMSection).filter(
            models.IEMSection.section == section
        ).order_by(models.IEMSection.id.asc()).first()
        if not section_row:
            return []
        query = query.filter(models.LMSLessonSchedule.section_id == section_row.id)
    if date:
        query = query.filter(models.LMSLessonSchedule.plan_date == date)
    if academic_batch_id is not None:
        query = query.filter(models.LMSLessonSchedule.academic_batch_id == academic_batch_id)
    if semester_id is not None:
        query = query.filter(models.LMSLessonSchedule.semester_id == semester_id)
    if course_id is not None:
        query = query.filter(models.LMSLessonSchedule.crs_id == course_id)

    rows = query.order_by(
        models.LMSLessonSchedule.plan_date.asc(),
        models.LMSLessonSchedule.start_time.asc()
    ).all()

    return [
        {
            "lls_id": row.lls_id,
            "crs_id": row.crs_id,
            "plan_date": row.plan_date,
            "start_time": _format_time_value(row.start_time),
            "end_time": _format_time_value(row.end_time),
            "section_id": row.section_id,
            "academic_batch_id": row.academic_batch_id,
            "semester_id": row.semester_id,
        }
        for row in rows
    ]


# --- 5. List Scheduled Classes API ---
@router.get("/timetable/scheduled-classes")
def list_scheduled_classes(
    section: Optional[str] = None,
    date: Optional[str] = None,
    academic_batch_id: Optional[int] = None,
    semester_id: Optional[int] = None,
    course_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    data = _scheduled_classes_array(section, date, academic_batch_id, semester_id, course_id, db)
    return _success_response(data)


# --- 6. Edit Scheduled Class API ---
@router.put("/timetable/scheduled-classes/{class_id}", response_model=ScheduledClassOut)
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
@router.delete("/timetable/scheduled-classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scheduled_class(class_id: int, db: Session = Depends(get_db)):
    db_class = db.query(models.IEMSCustomTimeTable).filter(
        models.IEMSCustomTimeTable.id == class_id
    ).first()
    if not db_class:
        raise HTTPException(status_code=404, detail="Scheduled class not found")

    db.delete(db_class)
    db.commit()
    return None


router.add_api_route("/comman_function/schedule-class", save_schedule, methods=["POST"])
router.add_api_route("/comman_function/check-duplicate", check_duplicate, methods=["POST"])
router.add_api_route("/comman_function/scheduled-classes", _scheduled_classes_array, methods=["GET"])
router.add_api_route("/common_function/scheduled-classes", _scheduled_classes_array, methods=["GET"])
router.add_api_route("/comman_function/add-extra-class", add_extra_class, methods=["POST"])
router.add_api_route("/comman_function/topic-lessons", get_topic_lessons, methods=["GET"])
