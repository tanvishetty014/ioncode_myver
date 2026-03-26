from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ...db import models
from app.access_control.schemas.curriculum_schemas import (
    ScheduledClassOut, ScheduledClassUpdate
)

# DO NOT TOUCH (partner code)
from app.api.v1.ems_module.comman_functions.comman_function import (
    list_batch_sections,
    list_course_types,
    list_courses,
)

from app.access_control.services import timetable_service
from ...core.database import get_db

router = APIRouter(tags=["Curriculum & Scheduling"])


def _success_response(data, message="Success"):
    return JSONResponse(
        status_code=200,
        content={"status": True, "message": message, "data": jsonable_encoder(data)}
    )


# --- 1. List Curriculum API ---
@router.get("/curriculums")
def get_curriculums(db: Session = Depends(get_db)):
    try:
        curriculums = db.query(models.IEMSCurriculum).all()
        data = [
            {
                "crclm_id": row.crclm_id,
                "start_year": row.start_year,
                "pgm_id": row.pgm_id,
                "dept_id": row.dept_id,
                "name": f"Batch {row.start_year}"
            }
            for row in curriculums
        ]
        return _success_response(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 2. List Terms API ---
@router.get("/curriculums/{crclm_id}/terms")
def get_terms_by_curriculum(crclm_id: int, db: Session = Depends(get_db)):
    try:
        terms = db.query(models.IEMSCrclmTerm).filter(
            models.IEMSCrclmTerm.crclm_id == crclm_id
        ).all()

        data = [
            {
                "crclm_term_id": r.crclm_term_id,
                "term_name": r.term_name
            }
            for r in terms
        ]
        return _success_response(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- 3. List Sections API ---
@router.get("/curriculums/{crclm_id}/terms/{crclm_term_id}/sections")
def get_sections(crclm_id: int, crclm_term_id: int, db: Session = Depends(get_db)):
    try:
        sections = db.query(models.IEMSection).filter(
            models.IEMSection.academic_batch_id == crclm_id,
            models.IEMSection.semester_id == crclm_term_id
        ).all()

        data = [
            {
                "section_id": s.id,
                "section_name": s.section
            }
            for s in sections if s.section
        ]

        return _success_response(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- DO NOT CHANGE: YOUR PARTNER'S WORK ---
router.add_api_route("/api/v1/comman_function/course-types", list_course_types, methods=["GET", "POST"])
router.add_api_route("/api/v1/comman_function/courses", list_courses, methods=["GET", "POST"])
router.add_api_route("/api/v1/comman_function/batch-sections", list_batch_sections, methods=["GET", "POST"])