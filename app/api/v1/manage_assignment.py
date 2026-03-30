from datetime import datetime
from typing import Optional, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...utils.http_return_helper import returnSuccess, returnException

router = APIRouter(prefix="/assignment", tags=["Manage Assignment"])


# Carries upload metadata for assignment-level documents.
class AssignmentUploadItem(BaseModel):
    file_name: str
    file_path: str


# Carries payload for creating a new assignment.
class AssignmentCreateRequest(BaseModel):
    assignment_name: str = Field(..., min_length=1)
    additional_info: Optional[str] = None
    academic_batch_id: Optional[int] = None
    semester_id: Optional[int] = None
    crs_id: Optional[int] = None
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    status: int = 1
    assess_attain_flag: int = 0
    created_by: int
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    bloom_ids: list[int] = Field(default_factory=list)
    clo_ids: list[int] = Field(default_factory=list)
    student_ids: list[int] = Field(default_factory=list)
    uploads: list[AssignmentUploadItem] = Field(default_factory=list)


# Carries payload for updating an existing assignment.
class AssignmentUpdateRequest(BaseModel):
    assignment_name: Optional[str] = None
    additional_info: Optional[str] = None
    academic_batch_id: Optional[int] = None
    semester_id: Optional[int] = None
    crs_id: Optional[int] = None
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[int] = None
    assess_attain_flag: Optional[int] = None
    modified_by: int
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    bloom_ids: Optional[list[int]] = None
    clo_ids: Optional[list[int]] = None
    uploads: Optional[list[AssignmentUploadItem]] = None


# Carries payload for sharing assignment with selected students.
class AssignmentShareRequest(BaseModel):
    student_ids: list[int] = Field(default_factory=list)
    created_by: int


# Carries payload for reviewing student assignment submission.
class AssignmentReviewRequest(BaseModel):
    action: Literal["approve", "rework", "pending"]
    secured_marks: Optional[int] = None
    remark: Optional[str] = None
    assignment_justification: Optional[str] = None
    current_comments: Optional[str] = None
    remark_file_name: Optional[str] = None
    remark_file_path: Optional[str] = None
    modified_by: int


# Checks if a table exists so optional writes can be safely handled.
def _table_exists(db: Session, table_name: str) -> bool:
    exists = db.execute(
        text(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = :table_name
            """
        ),
        {"table_name": table_name},
    ).scalar()
    return bool(exists)


# Fetches batches, semesters, courses, and sections for assignment filters.
@router.get("/meta/options")
def get_assignment_options(
    academic_batch_id: Optional[int] = Query(default=None),
    semester_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    batches = db.execute(text("SELECT academic_batch_id, academic_batch_code, academic_batch_desc FROM iems_academic_batch ORDER BY academic_batch_id DESC")).mappings().all()

    semester_query = "SELECT semester_id, semester, semester_desc, academic_batch_id FROM iems_semester WHERE 1=1"
    semester_params = {}
    if academic_batch_id is not None:
        semester_query += " AND academic_batch_id = :academic_batch_id"
        semester_params["academic_batch_id"] = academic_batch_id
    semester_query += " ORDER BY semester_id DESC"
    semesters = db.execute(text(semester_query), semester_params).mappings().all()

    course_query = "SELECT crs_id, crs_code, crs_title, academic_batch_id, semester FROM iems_courses WHERE 1=1"
    course_params = {}
    if academic_batch_id is not None:
        course_query += " AND academic_batch_id = :academic_batch_id"
        course_params["academic_batch_id"] = academic_batch_id
    if semester_id is not None:
        course_query += " AND semester = (SELECT semester FROM iems_semester WHERE semester_id = :semester_id)"
        course_params["semester_id"] = semester_id
    course_query += " ORDER BY crs_id DESC"
    courses = db.execute(text(course_query), course_params).mappings().all()

    section_query = "SELECT id AS section_id, section, academic_batch_id, semester_id FROM iems_section WHERE 1=1"
    section_params = {}
    if academic_batch_id is not None:
        section_query += " AND academic_batch_id = :academic_batch_id"
        section_params["academic_batch_id"] = academic_batch_id
    if semester_id is not None:
        section_query += " AND semester_id = :semester_id"
        section_params["semester_id"] = semester_id
    section_query += " ORDER BY id DESC"
    sections = db.execute(text(section_query), section_params).mappings().all()

    return returnSuccess({"academic_batches": batches, "semesters": semesters, "courses": courses, "sections": sections})


# Fetches topics based on selected batch, semester, and course for assignment creation.
@router.get("/meta/topics")
def get_assignment_topics(academic_batch_id: int, semester_id: int, crs_id: int, db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            "SELECT topic_id, topic_code, topic_title, course_id, semester_id, academic_batch_id FROM cudos_topic WHERE academic_batch_id = :academic_batch_id AND semester_id = :semester_id AND course_id = :crs_id ORDER BY topic_id DESC"
        ),
        {"academic_batch_id": academic_batch_id, "semester_id": semester_id, "crs_id": crs_id},
    ).mappings().all()
    return returnSuccess({"total": len(rows), "items": rows})


# Fetches bloom levels available for assignment mapping.
@router.get("/meta/bloom-levels")
def get_bloom_levels(db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT bloom_id, bloom_name, bloom_code FROM cudos_bloom_level ORDER BY bloom_id ASC")).mappings().all()
    return returnSuccess(rows)


# Fetches CLO list for the selected course to support assignment mapping.
@router.get("/meta/clos")
def get_clos_for_course(crs_id: int, db: Session = Depends(get_db)):
    rows = db.execute(text("SELECT clo_id, clo_name, clo_code, crs_id FROM cudos_clo WHERE crs_id = :crs_id ORDER BY clo_id ASC"), {"crs_id": crs_id}).mappings().all()
    return returnSuccess(rows)


# Fetches student list for sharing assignment based on selected class filters.
@router.get("/meta/students")
def get_students_for_assignment(
    academic_batch_id: Optional[int] = Query(default=None),
    semester_id: Optional[int] = Query(default=None),
    section: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = "SELECT student_id, usno, name, first_name, last_name, academic_batch_id, current_semester, section FROM iems_students WHERE status = 1 AND IFNULL(delete_status, 0) = 0"
    params = {}
    if academic_batch_id is not None:
        query += " AND academic_batch_id = :academic_batch_id"
        params["academic_batch_id"] = academic_batch_id
    if semester_id is not None:
        query += " AND current_semester = (SELECT semester FROM iems_semester WHERE semester_id = :semester_id)"
        params["semester_id"] = semester_id
    if section is not None and section.strip():
        query += " AND section = :section"
        params["section"] = section.strip()
    query += " ORDER BY student_id DESC"
    rows = db.execute(text(query), params).mappings().all()
    return returnSuccess({"total": len(rows), "items": rows})

# Creates assignment, maps bloom/CLO, and optionally shares with students.
@router.post("/create")
def create_assignment(payload: AssignmentCreateRequest, db: Session = Depends(get_db)):
    if not payload.assignment_name.strip():
        return returnException("assignment_name is required")

    try:
        # Inserts assignment header into LMS assignment table.
        assignment_result = db.execute(
            text(
                """
                INSERT INTO lms_manage_assignment
                (
                    assignment_name, additional_info, file_name, file_path,
                    academic_batch_id, semester_id, crs_id, issue_date, due_date,
                    status, assess_attain_flag, created_by, created_date
                )
                VALUES
                (
                    :assignment_name, :additional_info, :file_name, :file_path,
                    :academic_batch_id, :semester_id, :crs_id, :issue_date, :due_date,
                    :status, :assess_attain_flag, :created_by, :created_date
                )
                """
            ),
            {
                "assignment_name": payload.assignment_name.strip(),
                "additional_info": payload.additional_info,
                "file_name": payload.file_name,
                "file_path": payload.file_path,
                "academic_batch_id": payload.academic_batch_id,
                "semester_id": payload.semester_id,
                "crs_id": payload.crs_id,
                "issue_date": payload.issue_date,
                "due_date": payload.due_date,
                "status": payload.status,
                "assess_attain_flag": payload.assess_attain_flag,
                "created_by": payload.created_by,
                "created_date": datetime.now(),
            },
        )
        lms_assignment_id = assignment_result.lastrowid

        # Maps selected bloom levels with the created assignment.
        for bloom_id in payload.bloom_ids:
            db.execute(
                text("INSERT INTO lms_assignment_bloom_mapping (lms_assignment_id, bloom_id, created_by, created_date) VALUES (:lms_assignment_id, :bloom_id, :created_by, :created_date)"),
                {"lms_assignment_id": lms_assignment_id, "bloom_id": bloom_id, "created_by": payload.created_by, "created_date": datetime.now()},
            )

        # Maps selected CLOs with the created assignment.
        for clo_id in payload.clo_ids:
            db.execute(
                text("INSERT INTO lms_assignment_clo_mapping (lms_assignment_id, clo_id, created_by, created_date) VALUES (:lms_assignment_id, :clo_id, :created_by, :created_date)"),
                {"lms_assignment_id": lms_assignment_id, "clo_id": clo_id, "created_by": payload.created_by, "created_date": datetime.now()},
            )

        # Stores assignment-level uploads when upload map table exists.
        if payload.uploads and _table_exists(db, "lms_map_assignment_upload"):
            for upload in payload.uploads:
                db.execute(
                    text("INSERT INTO lms_map_assignment_upload (lms_assignment_id, file_name, file_path, created_by, created_date) VALUES (:lms_assignment_id, :file_name, :file_path, :created_by, :created_date)"),
                    {"lms_assignment_id": lms_assignment_id, "file_name": upload.file_name, "file_path": upload.file_path, "created_by": payload.created_by, "created_date": datetime.now()},
                )

        # Shares assignment with selected students on create when ids are provided.
        for student_id in payload.student_ids:
            student_row = db.execute(text("SELECT student_id, usno FROM iems_students WHERE student_id = :student_id LIMIT 1"), {"student_id": student_id}).mappings().first()
            if not student_row:
                continue
            db.execute(
                text("INSERT INTO lms_map_assignment_to_students (lms_assignment_id, ssd_id, student_usn, created_by, created_date) VALUES (:lms_assignment_id, :ssd_id, :student_usn, :created_by, :created_date)"),
                {"lms_assignment_id": lms_assignment_id, "ssd_id": student_row["student_id"], "student_usn": student_row["usno"], "created_by": payload.created_by, "created_date": datetime.now()},
            )

        db.commit()
        return returnSuccess({"lms_assignment_id": lms_assignment_id, "bloom_count": len(payload.bloom_ids), "clo_count": len(payload.clo_ids), "shared_students_count": len(payload.student_ids)}, "Assignment created successfully")
    except Exception as exc:
        db.rollback()
        return returnException(f"Failed to create assignment: {str(exc)}")


# Fetches paginated assignment list with optional filter criteria.
@router.get("/list")
def get_assignments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    academic_batch_id: Optional[int] = Query(default=None),
    semester_id: Optional[int] = Query(default=None),
    crs_id: Optional[int] = Query(default=None),
    created_by: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    base_filter = " WHERE 1=1 "
    params = {}
    if academic_batch_id is not None:
        base_filter += " AND a.academic_batch_id = :academic_batch_id"
        params["academic_batch_id"] = academic_batch_id
    if semester_id is not None:
        base_filter += " AND a.semester_id = :semester_id"
        params["semester_id"] = semester_id
    if crs_id is not None:
        base_filter += " AND a.crs_id = :crs_id"
        params["crs_id"] = crs_id
    if created_by is not None:
        base_filter += " AND a.created_by = :created_by"
        params["created_by"] = created_by

    total = db.execute(text(f"SELECT COUNT(*) FROM lms_manage_assignment a {base_filter}"), params).scalar() or 0
    offset = (page - 1) * page_size
    rows = db.execute(
        text(
            f"""
            SELECT
                a.lms_assignment_id, a.assignment_name, a.additional_info, a.file_name, a.file_path,
                a.academic_batch_id, a.semester_id, a.crs_id, a.issue_date, a.due_date,
                a.status, a.assess_attain_flag, a.created_by, a.created_date,
                (SELECT COUNT(*) FROM lms_map_assignment_to_students ms WHERE ms.lms_assignment_id = a.lms_assignment_id) AS shared_students_count
            FROM lms_manage_assignment a
            {base_filter}
            ORDER BY a.lms_assignment_id DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        {**params, "limit": page_size, "offset": offset},
    ).mappings().all()

    return returnSuccess({"page": page, "page_size": page_size, "total": int(total), "items": rows})


# Fetches assignment full details for edit and review screens.
@router.get("/{assignment_id}")
def get_assignment_details(assignment_id: int, db: Session = Depends(get_db)):
    assignment = db.execute(text("SELECT * FROM lms_manage_assignment WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id}).mappings().first()
    if not assignment:
        return returnException("Assignment not found")

    bloom_rows = db.execute(text("SELECT bloom_id FROM lms_assignment_bloom_mapping WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id}).mappings().all()
    clo_rows = db.execute(text("SELECT clo_id FROM lms_assignment_clo_mapping WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id}).mappings().all()
    shared_students = db.execute(
        text("SELECT map_assignment_student_id, ssd_id, student_usn, file_name, file_path, seen_on, accept_rework_flag, secured_marks, remark, assignment_justification, current_comments FROM lms_map_assignment_to_students WHERE lms_assignment_id = :assignment_id ORDER BY map_assignment_student_id DESC"),
        {"assignment_id": assignment_id},
    ).mappings().all()

    upload_rows = []
    if _table_exists(db, "lms_map_assignment_upload"):
        upload_rows = db.execute(text("SELECT file_name, file_path FROM lms_map_assignment_upload WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id}).mappings().all()

    return returnSuccess({"assignment": assignment, "bloom_ids": [row["bloom_id"] for row in bloom_rows], "clo_ids": [row["clo_id"] for row in clo_rows], "shared_students": shared_students, "uploads": upload_rows})

# Updates assignment details and replaces bloom/CLO/upload mappings.
@router.put("/{assignment_id}")
def update_assignment(assignment_id: int, payload: AssignmentUpdateRequest, db: Session = Depends(get_db)):
    exists = db.execute(text("SELECT lms_assignment_id FROM lms_manage_assignment WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id}).scalar()
    if not exists:
        return returnException("Assignment not found")

    try:
        # Updates assignment master row with editable fields.
        db.execute(
            text(
                """
                UPDATE lms_manage_assignment
                SET
                    assignment_name = COALESCE(:assignment_name, assignment_name),
                    additional_info = COALESCE(:additional_info, additional_info),
                    file_name = COALESCE(:file_name, file_name),
                    file_path = COALESCE(:file_path, file_path),
                    academic_batch_id = COALESCE(:academic_batch_id, academic_batch_id),
                    semester_id = COALESCE(:semester_id, semester_id),
                    crs_id = COALESCE(:crs_id, crs_id),
                    issue_date = COALESCE(:issue_date, issue_date),
                    due_date = COALESCE(:due_date, due_date),
                    status = COALESCE(:status, status),
                    assess_attain_flag = COALESCE(:assess_attain_flag, assess_attain_flag),
                    modfified_by = :modified_by,
                    modified_date = :modified_date
                WHERE lms_assignment_id = :assignment_id
                """
            ),
            {
                "assignment_name": payload.assignment_name.strip() if payload.assignment_name else None,
                "additional_info": payload.additional_info,
                "file_name": payload.file_name,
                "file_path": payload.file_path,
                "academic_batch_id": payload.academic_batch_id,
                "semester_id": payload.semester_id,
                "crs_id": payload.crs_id,
                "issue_date": payload.issue_date,
                "due_date": payload.due_date,
                "status": payload.status,
                "assess_attain_flag": payload.assess_attain_flag,
                "modified_by": payload.modified_by,
                "modified_date": datetime.now(),
                "assignment_id": assignment_id,
            },
        )

        # Replaces bloom mappings when bloom list is passed.
        if payload.bloom_ids is not None:
            db.execute(text("DELETE FROM lms_assignment_bloom_mapping WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id})
            for bloom_id in payload.bloom_ids:
                db.execute(text("INSERT INTO lms_assignment_bloom_mapping (lms_assignment_id, bloom_id, created_by, created_date) VALUES (:assignment_id, :bloom_id, :created_by, :created_date)"), {"assignment_id": assignment_id, "bloom_id": bloom_id, "created_by": payload.modified_by, "created_date": datetime.now()})

        # Replaces CLO mappings when clo list is passed.
        if payload.clo_ids is not None:
            db.execute(text("DELETE FROM lms_assignment_clo_mapping WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id})
            for clo_id in payload.clo_ids:
                db.execute(text("INSERT INTO lms_assignment_clo_mapping (lms_assignment_id, clo_id, created_by, created_date) VALUES (:assignment_id, :clo_id, :created_by, :created_date)"), {"assignment_id": assignment_id, "clo_id": clo_id, "created_by": payload.modified_by, "created_date": datetime.now()})

        # Replaces upload mappings when upload list is passed and table exists.
        if payload.uploads is not None and _table_exists(db, "lms_map_assignment_upload"):
            db.execute(text("DELETE FROM lms_map_assignment_upload WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id})
            for upload in payload.uploads:
                db.execute(text("INSERT INTO lms_map_assignment_upload (lms_assignment_id, file_name, file_path, created_by, created_date) VALUES (:lms_assignment_id, :file_name, :file_path, :created_by, :created_date)"), {"lms_assignment_id": assignment_id, "file_name": upload.file_name, "file_path": upload.file_path, "created_by": payload.modified_by, "created_date": datetime.now()})

        db.commit()
        return returnSuccess({"lms_assignment_id": assignment_id}, "Assignment updated successfully")
    except Exception as exc:
        db.rollback()
        return returnException(f"Failed to update assignment: {str(exc)}")


# Shares an existing assignment with selected students.
@router.post("/{assignment_id}/share")
def share_assignment_with_students(assignment_id: int, payload: AssignmentShareRequest, db: Session = Depends(get_db)):
    exists = db.execute(text("SELECT lms_assignment_id FROM lms_manage_assignment WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id}).scalar()
    if not exists:
        return returnException("Assignment not found")
    if not payload.student_ids:
        return returnException("student_ids is required")

    inserted = 0
    skipped = 0
    try:
        # Inserts student sharing records and skips already shared students.
        for student_id in payload.student_ids:
            student_row = db.execute(text("SELECT student_id, usno FROM iems_students WHERE student_id = :student_id LIMIT 1"), {"student_id": student_id}).mappings().first()
            if not student_row:
                skipped += 1
                continue

            existing_map = db.execute(text("SELECT map_assignment_student_id FROM lms_map_assignment_to_students WHERE lms_assignment_id = :assignment_id AND ssd_id = :student_id LIMIT 1"), {"assignment_id": assignment_id, "student_id": student_id}).scalar()
            if existing_map:
                skipped += 1
                continue

            db.execute(
                text("INSERT INTO lms_map_assignment_to_students (lms_assignment_id, ssd_id, student_usn, created_by, created_date) VALUES (:assignment_id, :ssd_id, :student_usn, :created_by, :created_date)"),
                {"assignment_id": assignment_id, "ssd_id": student_row["student_id"], "student_usn": student_row["usno"], "created_by": payload.created_by, "created_date": datetime.now()},
            )
            inserted += 1

        db.commit()
        return returnSuccess({"inserted": inserted, "skipped": skipped}, "Assignment shared with students")
    except Exception as exc:
        db.rollback()
        return returnException(f"Failed to share assignment: {str(exc)}")


# Fetches assignments shared with students for list and tracking screens.
@router.get("/shared/list")
def get_shared_assignments(student_id: Optional[int] = Query(default=None), created_by: Optional[int] = Query(default=None), db: Session = Depends(get_db)):
    query = """
        SELECT
            ms.map_assignment_student_id,
            ms.lms_assignment_id,
            ms.ssd_id,
            ms.student_usn,
            ms.file_name AS student_file_name,
            ms.file_path AS student_file_path,
            ms.seen_on,
            ms.accept_rework_flag,
            ms.secured_marks,
            ms.remark,
            ms.assignment_justification,
            ms.current_comments,
            a.assignment_name,
            a.additional_info,
            a.file_name AS assignment_file_name,
            a.file_path AS assignment_file_path,
            a.issue_date,
            a.due_date,
            a.created_by
        FROM lms_map_assignment_to_students ms
        JOIN lms_manage_assignment a ON a.lms_assignment_id = ms.lms_assignment_id
        WHERE 1=1
    """
    params = {}
    if student_id is not None:
        query += " AND ms.ssd_id = :student_id"
        params["student_id"] = student_id
    if created_by is not None:
        query += " AND a.created_by = :created_by"
        params["created_by"] = created_by
    query += " ORDER BY ms.map_assignment_student_id DESC"
    rows = db.execute(text(query), params).mappings().all()
    return returnSuccess({"total": len(rows), "items": rows})

# Fetches downloadable assignment and submission documents for faculty or students.
@router.get("/{assignment_id}/documents")
def get_assignment_documents(
    assignment_id: int,
    viewer_type: Literal["faculty", "student"],
    viewer_id: int,
    db: Session = Depends(get_db),
):
    assignment = db.execute(text("SELECT lms_assignment_id, assignment_name, file_name, file_path, created_by FROM lms_manage_assignment WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id}).mappings().first()
    if not assignment:
        return returnException("Assignment not found")

    # Returns assignment and submission docs for assignment owner faculty.
    if viewer_type == "faculty":
        if int(assignment["created_by"] or 0) != viewer_id:
            return returnException("You are not allowed to view these documents")
        submissions = db.execute(text("SELECT ssd_id, student_usn, file_name, file_path, remark_file_name, remark_file_path FROM lms_map_assignment_to_students WHERE lms_assignment_id = :assignment_id ORDER BY map_assignment_student_id DESC"), {"assignment_id": assignment_id}).mappings().all()
        return returnSuccess({"assignment": assignment, "submissions": submissions})

    # Returns assignment docs and the student's own submission documents.
    mapping_row = db.execute(text("SELECT map_assignment_student_id, ssd_id, student_usn, file_name, file_path, remark_file_name, remark_file_path FROM lms_map_assignment_to_students WHERE lms_assignment_id = :assignment_id AND ssd_id = :viewer_id LIMIT 1"), {"assignment_id": assignment_id, "viewer_id": viewer_id}).mappings().first()
    if not mapping_row:
        return returnException("You are not mapped to this assignment")
    return returnSuccess({"assignment": assignment, "submission": mapping_row})


# Approves, rejects for rework, or resets student submission review status.
@router.post("/review/{map_assignment_student_id}")
def review_assignment_submission(map_assignment_student_id: int, payload: AssignmentReviewRequest, db: Session = Depends(get_db)):
    flag_map = {"pending": 0, "approve": 1, "rework": 2}
    review_flag = flag_map[payload.action]

    exists = db.execute(text("SELECT map_assignment_student_id FROM lms_map_assignment_to_students WHERE map_assignment_student_id = :map_assignment_student_id"), {"map_assignment_student_id": map_assignment_student_id}).scalar()
    if not exists:
        return returnException("Assignment submission mapping not found")

    try:
        # Updates faculty review details against student assignment row.
        db.execute(
            text(
                """
                UPDATE lms_map_assignment_to_students
                SET
                    accept_rework_flag = :accept_rework_flag,
                    secured_marks = :secured_marks,
                    remark = :remark,
                    assignment_justification = :assignment_justification,
                    current_comments = :current_comments,
                    remark_file_name = :remark_file_name,
                    remark_file_path = :remark_file_path,
                    modified_by = :modified_by,
                    modified_date = :modified_date
                WHERE map_assignment_student_id = :map_assignment_student_id
                """
            ),
            {
                "accept_rework_flag": review_flag,
                "secured_marks": payload.secured_marks,
                "remark": payload.remark,
                "assignment_justification": payload.assignment_justification,
                "current_comments": payload.current_comments,
                "remark_file_name": payload.remark_file_name,
                "remark_file_path": payload.remark_file_path,
                "modified_by": payload.modified_by,
                "modified_date": datetime.now(),
                "map_assignment_student_id": map_assignment_student_id,
            },
        )
        db.commit()
        return returnSuccess({"map_assignment_student_id": map_assignment_student_id, "accept_rework_flag": review_flag}, "Assignment review saved successfully")
    except Exception as exc:
        db.rollback()
        return returnException(f"Failed to save assignment review: {str(exc)}")


# Deletes assignment and all linked mappings safely.
@router.delete("/{assignment_id}")
def delete_assignment(assignment_id: int, db: Session = Depends(get_db)):
    exists = db.execute(text("SELECT lms_assignment_id FROM lms_manage_assignment WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id}).scalar()
    if not exists:
        return returnException("Assignment not found")

    try:
        # Removes dependent records before deleting assignment header row.
        db.execute(text("DELETE FROM lms_map_assignment_to_students WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id})
        db.execute(text("DELETE FROM lms_assignment_bloom_mapping WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id})
        db.execute(text("DELETE FROM lms_assignment_clo_mapping WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id})
        if _table_exists(db, "lms_map_assignment_upload"):
            db.execute(text("DELETE FROM lms_map_assignment_upload WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id})
        db.execute(text("DELETE FROM lms_manage_assignment WHERE lms_assignment_id = :assignment_id"), {"assignment_id": assignment_id})
        db.commit()
        return returnSuccess({"lms_assignment_id": assignment_id}, "Assignment deleted successfully")
    except Exception as exc:
        db.rollback()
        return returnException(f"Failed to delete assignment: {str(exc)}")
