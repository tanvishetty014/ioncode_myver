from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
from app.core.database import get_db
from app.api.v1.material.material_schema import *
from app.db.models import *

router = APIRouter()


# ── Dropdown helpers (no auth required, consistent with material routes) ────────

@router.get("/dropdown/batches")
def get_batch_dropdown(db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT academic_batch_id, academic_batch_code, academic_batch_desc FROM iems_academic_batch ORDER BY academic_batch_id DESC LIMIT 50"
    )).mappings().all()
    return [dict(r) for r in rows]


@router.get("/dropdown/semesters")
def get_semester_dropdown(academic_batch_id: int, db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT semester_id, semester, semester_desc FROM iems_semester WHERE academic_batch_id = :bid ORDER BY semester"
    ), {"bid": academic_batch_id}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/dropdown/courses")
def get_course_dropdown(academic_batch_id: int, semester_id: int, db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT crs_id, crs_code, crs_title FROM iems_courses WHERE academic_batch_id = :bid ORDER BY crs_code"
    ), {"bid": academic_batch_id}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/dropdown/sections")
def get_section_dropdown(academic_batch_id: int, semester_id: int, db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT id, section FROM iems_section WHERE academic_batch_id = :bid ORDER BY section"
    ), {"bid": academic_batch_id}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/dropdown/all_sections")
def get_all_sections(db: Session = Depends(get_db)):
    """Returns every section row — used when batch/semester data doesn't exist yet."""
    rows = db.execute(text(
        "SELECT id, section FROM iems_section ORDER BY section"
    )).mappings().all()
    return [dict(r) for r in rows]



@router.post("/create_material")
def create_material(
    academic_batch_id: int = Form(0),
    semester_id: int = Form(0),
    course_id: int = Form(0),
    section_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(None),
    created_by: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    # ---------- FILE TYPE VALIDATION ----------
    allowed_types = ["pdf","doc","docx","ppt","pptx"]

    file_ext = file.filename.split(".")[-1]

    if file_ext not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type")


    # ---------- FILE SAVE ----------
    upload_folder = "uploads/materials"

    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    file_path = f"{upload_folder}/{file.filename}"

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())


    # ---------- DB INSERT ----------
    # Convert 0 → None so FK constraints aren't violated when batch/semester data doesn't exist
    batch_id_val = academic_batch_id if academic_batch_id and academic_batch_id != 0 else None
    semester_id_val = semester_id if semester_id and semester_id != 0 else None
    course_id_val = course_id if course_id and course_id != 0 else None

    material = LMSCourseMaterialUpload(
    document_name=title,
    file_name=file.filename,
    docment_url=file_path,
    description=description,
    academic_batch_id=batch_id_val,
    semester_id=semester_id_val,
    crs_id=course_id_val,
    section_ids=str(section_id),
    topic_ids=None,
    created_by=created_by,
    update_cnt=0
    )

    db.add(material)
    db.commit()
    db.refresh(material)

    return {
        "status": True,
        "message": "Material uploaded successfully"
    }


@router.post("/material_list")
def material_list(request: MaterialListRequest, db: Session = Depends(get_db)):

    # Always filter by section_id (reliable since it's always stored)
    query = db.query(LMSCourseMaterialUpload).filter(
        LMSCourseMaterialUpload.section_ids.contains(str(request.section_id))
    )

    # Only apply batch/semester/course filters when non-zero values are provided
    # (Materials uploaded without batch data have NULL for these fields)
    if request.academic_batch_id and request.academic_batch_id != 0:
        query = query.filter(LMSCourseMaterialUpload.academic_batch_id == request.academic_batch_id)
    if request.semester_id and request.semester_id != 0:
        query = query.filter(LMSCourseMaterialUpload.semester_id == request.semester_id)
    if request.course_id and request.course_id != 0:
        query = query.filter(LMSCourseMaterialUpload.crs_id == request.course_id)

    materials = query.all()
    return materials


class StudentListRequest(BaseModel):
    section_id: int

@router.post("/student_list")
def student_list(request: StudentListRequest, db: Session = Depends(get_db)):
    students = db.query(IEMSUsers).filter(
        IEMSUsers.is_student == 1
    ).all()

    return [
        {
            "value": s.id,
            "label": f"{s.first_name} {s.last_name}"
        }
        for s in students
    ]

@router.post("/share_material")
def share_material(request: ShareMaterialRequest, db: Session = Depends(get_db)):

    for student_usn in request.student_usns:

        mapping = LMSMapShareMaterialsToStudent(
            ssd_id=None,
            mat_id=request.material_id,
            academic_batch_id=request.academic_batch_id,
            section_id=request.section_id,
            student_usn=student_usn
        )

        db.add(mapping)

    db.commit()

    return {
        "status": True,
        "message": "Material shared successfully"
    }

@router.get("/download_material/{mat_id}")
def download_material(mat_id: int, db: Session = Depends(get_db)):

    material = db.query(LMSCourseMaterialUpload).filter(
        LMSCourseMaterialUpload.mat_id == mat_id
    ).first()

    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    return FileResponse(material.docment_url, filename=material.file_name)

@router.put("/update_material/{material_id}")
def update_material(
    material_id: int,
    title: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):

    material = db.query(LMSCourseMaterialUpload).filter(
        LMSCourseMaterialUpload.mat_id == material_id
    ).first()

    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    # update fields
    material.document_name = title
    material.description = description

    # if new file uploaded
    if file:
        upload_folder = "uploads/materials"

        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        file_path = f"{upload_folder}/{file.filename}"

        with open(file_path, "wb") as buffer:
            buffer.write(file.file.read())

        material.file_name = file.filename
        material.docment_url = file_path

    material.update_cnt = material.update_cnt + 1

    db.commit()
    db.refresh(material)

    return {
        "status": True,
        "message": "Material updated successfully"
    }
@router.post("/material_mapping_list")
def material_mapping_list(request: MaterialMappingRequest, db: Session = Depends(get_db)):

    mappings = db.query(LMSMapShareMaterialsToStudent).filter(
        LMSMapShareMaterialsToStudent.mat_id == request.material_id
    ).all()

    result = []

    for m in mappings:

        student = db.query(IEMSUsers).filter(
            IEMSUsers.usn == m.student_usn
        ).first()

        result.append({
            "student_usn": m.student_usn,
            "student_name": f"{student.first_name} {student.last_name}" if student else None,
            "section_id": m.section_id
        })

    return result
