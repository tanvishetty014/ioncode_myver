# curriculum_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional # Added Optional for query params

# Adjust these imports based on repository layout
from ...db import models
from app.access_control.schemas.curriculum_schemas import (
    CurriculumOut, TermOut, SectionOut, 
    TimeTableOut, ScheduledClassOut, ScheduledClassUpdate
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

# --- 1. List Curriculum API (UNTOUCHED) ---
@router.get("/timetable/curriculums", response_model=List[CurriculumOut])
def get_curriculums(db: Session = Depends(get_db)):
    curriculums = db.query(models.IEMSCurriculum).all()
    return curriculums

# --- 2. List Terms Based on Curriculum API (UNTOUCHED) ---
@router.get("/timetable/curriculums/{crclm_id}/terms", response_model=List[TermOut])
def get_terms_by_curriculum(crclm_id: int, db: Session = Depends(get_db)):
    terms = db.query(models.IEMSCrclmTerm).filter(
        models.IEMSCrclmTerm.crclm_id == crclm_id
    ).all()
    if not terms:
        return []
    return terms

# --- 3. List Section (UPDATED WITH PARTNER'S ERROR HANDLING) ---
@router.get("/timetable/curriculums/{crclm_id}/terms/{term_name}/sections", response_model=List[SectionOut])
def get_sections(crclm_id: int, term_name: str, db: Session = Depends(get_db)):
    try:
        sections = db.query(models.IEMSemTimeTable.section).filter(
            models.IEMSemTimeTable.term == term_name
        ).distinct().all()
        
        if not sections:
            return []
            
        return [{"section": sec[0]} for sec in sections if sec[0]]
    except Exception as e:
        print(f"ERROR in get_sections: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# --- 4. Fetch Scheduled Classes (NEW API ADDED BY PARTNER) ---
@router.get("/timetable/scheduled-classes")
def get_scheduled_classes(course_code: str, class_date: dt_date, section: str = None, db: Session = Depends(get_db)):
    """Fetch real scheduled classes for a specific course and date."""
    try:
        timings = timetable_service.get_scheduled_class_timings(db, course_code, class_date, section)
        return timings
    except Exception as e:
        print(f"ERROR in get_scheduled_classes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# --- COMMON FUNCTIONS (UNTOUCHED) ---
router.add_api_route("/comman_function/course-types", list_course_types, methods=["GET"])
router.add_api_route("/comman_function/courses", list_courses, methods=["POST"])
router.add_api_route("/comman_function/batch-sections", list_batch_sections, methods=["POST"])