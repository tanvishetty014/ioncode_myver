# curriculum_schemas.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class CurriculumOut(BaseModel):
    crclm_id: int
    start_year: int
    pgm_id: int
    dept_id: int

    class Config:
        from_attributes = True # use orm_mode = True if using Pydantic v1

class TermOut(BaseModel):
    crclm_term_id: int
    term_name: int
    crclm_id: int
    term_min_credits: str
    term_max_credits: str

    class Config:
        from_attributes = True

class SectionOut(BaseModel):
    section: str

class TimeTableOut(BaseModel):
    time_table_id: int
    crs_code: str
    start_time: str
    end_time: str
    section: str
    term: str

class ScheduledClassOut(BaseModel):
    id: int
    pgm_id: int
    dept_id: int
    academic_batch: str
    semester: int
    section: str
    date: date
    start_time: str
    end_time: str
    crs_code: str
    faculty_id: int
    status: str
    batch_name: str

    class Config:
        from_attributes = True

class ScheduledClassUpdate(BaseModel):
    date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    crs_code: Optional[str] = None
    faculty_id: Optional[int] = None
    status: Optional[str] = None
    batch_name: Optional[str] = None