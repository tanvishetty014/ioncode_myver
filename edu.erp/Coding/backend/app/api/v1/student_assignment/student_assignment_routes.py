from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from .student_assignment_schema import *

router = APIRouter( tags=["Student Assignment"])
from sqlalchemy import text
#routers
@router.post("/assignment_list")
def get_assignment_list(
    data: AssignmentListRequest,
    db: Session = Depends(get_db)
):
    try:
        query = text("""
    SELECT 
    lms_assignment_id AS assignment_id,
    assignment_name
    FROM lms_manage_assignment
    WHERE crs_id = :course_id
    AND semester_id = :semester_id
    AND academic_batch_id = :academic_batch_id
""")

        result = db.execute(query, {
            "course_id": data.course_id,
            "semester_id": data.semester_id,
            "academic_batch_id": data.academic_batch_id
        }).fetchall()

        return {
            "status": True,
            "data": [dict(row) for row in result]
        }

    except Exception as e:
        return {
            "status": False,
            "error": str(e)
        }
    
@router.post("/report")
def get_student_assignment_report(
    data: StudentAssignmentReportRequest,
    db: Session = Depends(get_db)
):
    try:
        query = text("""
        SELECT 
            map_assignment_student_id,
            student_usn,
            secured_marks,
            remark,
            file_path,
            seen_on
        FROM lms_map_assignment_to_students
        WHERE lms_assignment_id = :assignment_id
        """)

        result = db.execute(query, data.dict()).fetchall()

        return {
            "status": True,
            "data": [dict(row) for row in result]
        }

    except Exception as e:
        return {
            "status": False,
            "error": str(e)
        }