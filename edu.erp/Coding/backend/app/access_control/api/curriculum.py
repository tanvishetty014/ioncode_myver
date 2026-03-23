# curriculum_routes.py
from fastapi import APIRouter, Depends, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional

# Adjust these imports based on repository layout
from ...db import models
from app.access_control.schemas.curriculum_schemas import (
    ScheduledClassOut, ScheduledClassUpdate
)
from app.api.v1.ems_module.comman_functions.comman_function import (
    list_batch_sections,
    list_course_types,
    list_courses,
)

# Added only the imports your partner needs
from app.access_control.services import timetable_service
from datetime import date as dt_date

from ...core.database import get_db

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

# --- 1. List Curriculum API (UNTOUCHED) ---
@router.get("/timetable/curriculums")
def get_curriculums(db: Session = Depends(get_db)):
    curriculums = db.query(models.IEMSCurriculum).all()
    data = [
        {
            "crclm_id": row.crclm_id,
            "start_year": row.start_year,
            "pgm_id": row.pgm_id,
            "dept_id": row.dept_id,
        }
        for row in curriculums
    ]
    return _success_response(data)

# --- 2. List Terms Based on Curriculum API ---
@router.get("/timetable/curriculums/{crclm_id}/terms")
def get_terms_by_curriculum(crclm_id: int, db: Session = Depends(get_db)):
    terms = db.query(models.IEMSCrclmTerm).filter(
        models.IEMSCrclmTerm.crclm_id == crclm_id
    ).all()
    data = [
        {
            "crclm_term_id": row.crclm_term_id,
            "term_name": row.term_name,
            "crclm_id": row.crclm_id,
            "term_min_credits": row.term_min_credits,
            "term_max_credits": row.term_max_credits,
        }
        for row in terms
    ]
    return _success_response(data)

# List Section Based on Curriculum & Term
@router.get("/timetable/curriculums/{crclm_id}/terms/{crclm_term_id}/sections")
def get_sections(crclm_id: int, crclm_term_id: int, db: Session = Depends(get_db)):
    sections = db.query(models.IEMSection).filter(
        models.IEMSection.academic_batch_id == crclm_id,
        models.IEMSection.semester_id == crclm_term_id
    ).order_by(models.IEMSection.id.asc()).all()

    data = [
        {
            "section_id": row.id,
            "section_name": row.section,
        }
        for row in sections
        if row.section
    ]
    return _success_response(data)


router.add_api_route("/comman_function/course-types", list_course_types, methods=["GET"])
router.add_api_route("/comman_function/courses", list_courses, methods=["POST"])
router.add_api_route("/comman_function/batch-sections", list_batch_sections, methods=["POST"])