from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import date


class AttendanceRecord(BaseModel):
    regno: str
    usno: Optional[str] = None
    student_id: Optional[int] = None
    attendance_status: int  # 1-Finalize, 2-Draft, 0-Yet to take
    other_reason: Optional[str] = None
    is_extra_class: Optional[int] = 0


class AttendanceSavePayload(BaseModel):
    meta: Dict
    records: List[AttendanceRecord]


class LessonDatesResponse(BaseModel):
    dates: List[date]


class AttendanceSummaryStudent(BaseModel):
    name: str
    present: int
    absent: int


class AttendanceSummaryResponse(BaseModel):
    students: List[AttendanceSummaryStudent]
