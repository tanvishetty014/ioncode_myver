# curriculum_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

# Adjust these imports based on repository layout
from ...db import models
from app.access_control.schemas.curriculum_schemas import (
    CurriculumOut, TermOut, SectionOut, 
    TimeTableOut, ScheduledClassOut, ScheduledClassUpdate
)

from ...core.database import get_db

router = APIRouter(prefix="/timetable", tags=["Curriculum & Scheduling"])

# --- 1. List Curriculum API ---
@router.get("/curriculums", response_model=List[CurriculumOut])
def get_curriculums(db: Session = Depends(get_db)):
    curriculums = db.query(models.IEMSCurriculum).all()
    return curriculums

# --- 2. List Terms Based on Curriculum API ---
@router.get("/curriculums/{crclm_id}/terms", response_model=List[TermOut])
def get_terms_by_curriculum(crclm_id: int, db: Session = Depends(get_db)):
    terms = db.query(models.IEMSCrclmTerm).filter(
        models.IEMSCrclmTerm.crclm_id == crclm_id
    ).all()
    # Return an empty list when no terms found to match the declared List response_model
    if not terms:
        return []
    return terms

# List Section Based on Curriculum & Term
@router.get("/curriculums/{crclm_id}/terms/{term_name}/sections", response_model=List[SectionOut])
def get_sections(crclm_id: int, term_name: str, db: Session = Depends(get_db)):
    sections = db.query(models.IEMSemTimeTable.section).filter(
        models.IEMSemTimeTable.term == term_name
    ).distinct().all()
    return [{"section": sec[0]} for sec in sections if sec[0]]


