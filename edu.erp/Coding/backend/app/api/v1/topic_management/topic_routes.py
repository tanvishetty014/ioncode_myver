# ============================================================
# TOPIC MANAGEMENT APIs
# ============================================================
# These APIs manage topic master data and LMS topic mappings
# Key functionalities:
# - Academic batch, semester, course, and section listings
# - Topic master CRUD operations (create, read, update, delete)
# - Bulk import of topics to LMS mapping
# - Topic lesson schedule management
# - Extra topic addition for specific sections/instructors
# ============================================================

print("🔥 Topic Router Loaded")

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from typing import List


from app.core.database import get_db

# Models
from app.db.models import IEMSCourses, IEMSection, CudosTopic, LMSMapInstructorTopic, IEMSAcademicBatch, IEMSemester, TopicLessonSchedule, LMSMapPortionLS, MapCourseToCourseInstructor

# Schemas
from .topic_schema import (
    CourseListRequest,
    TopicSectionListRequest,
    TopicCreateRequest,
    TopicListRequest,
    ImportTopicsBulkRequest,
    EditTopicScheduleRequest,
    AddExtraTopicRequest
)

router = APIRouter()

# ==============================
# API 1 – Academic Batch List
# ==============================
@router.get("/Curriculum_list")
def academic_batch_list(db: Session = Depends(get_db)):

    batches = db.query(IEMSAcademicBatch).all()

    return batches

# ==============================
# API 2 – Semester List
# ==============================
@router.get("/semester_list(term_list)")
def semester_list(db: Session = Depends(get_db)):

    semesters = db.query(IEMSemester).all()

    return semesters

# ==============================
# API 3 – Course List
# ==============================
@router.post("/course_list")
def get_course_list(request: CourseListRequest, db: Session = Depends(get_db)):
    courses = db.query(IEMSCourses).filter(
        IEMSCourses.program_id == request.curriculum_id,
        IEMSCourses.semester == request.term_id
    ).all()

    return courses


# ==============================
# API 4 – Section List
# ==============================
@router.post("/section_list")
def get_section_list(request: TopicSectionListRequest, db: Session = Depends(get_db)):
    sections = db.query(IEMSection).filter(
        IEMSection.pgm_id == request.program_id,
        IEMSection.semester_id == request.semester
    ).all()

    return sections

# ==============================
# API 5 – Topic Master List to (List master topics based on academic batch, semester & course)
# ==============================
@router.post("/topic_list")
def topic_list(request: TopicListRequest, db: Session = Depends(get_db)):
    topics = db.query(CudosTopic).filter(
        CudosTopic.academic_batch_id == request.academic_batch_id,
        CudosTopic.semester_id == request.semester_id,
        CudosTopic.course_id == request.course_id
    ).all()

    return topics

# ==============================
# API 6 – Topic Master CREATE to Create topic
# ==============================
@router.post("/import_topic")
def import_topic(request: TopicCreateRequest, db: Session = Depends(get_db)):
    try:
        new_topic = CudosTopic(
            topic_code=request.topic_code,
            topic_title=request.topic_title,
            topic_content=request.topic_content,
            academic_batch_id=request.academic_batch_id,
            semester_id=request.semester_id,
            course_id=request.course_id,
            created_by=request.created_by,
            created_date=datetime.now()
        )

        db.add(new_topic)
        db.commit()
        db.refresh(new_topic)

        return {"message": "Topic created successfully"}

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Invalid academic_batch_id / semester_id / course_id"
        )



# ==============================
# API 7 – Update Topic
# ==============================
@router.put("/update_topic/{topic_id}")
def update_topic(topic_id: int, request: TopicCreateRequest, db: Session = Depends(get_db)):

    topic = db.query(CudosTopic).filter(
        CudosTopic.topic_id == topic_id
    ).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    try:
        topic.topic_code = request.topic_code
        topic.topic_title = request.topic_title
        topic.topic_content = request.topic_content
        topic.academic_batch_id = request.academic_batch_id
        topic.semester_id = request.semester_id
        topic.course_id = request.course_id
        topic.modified_by = request.created_by
        topic.modified_date = datetime.now()

        db.commit()
        db.refresh(topic)

        return {"message": "Topic updated successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==============================
# API 8 – Delete Topic
# ==============================
@router.delete("/delete_topic/{topic_id}")
def delete_topic(topic_id: int, db: Session = Depends(get_db)):

    topic = db.query(CudosTopic).filter(
        CudosTopic.topic_id == topic_id
    ).first()

    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    try:
        db.delete(topic)
        db.commit()
        return {"message": "Topic deleted successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==============================
# API 9 – BULK IMPORT TOPICS TO LMS MAPPING
# ==============================
@router.post("/import_topics_bulk")
def import_topics_bulk(request: ImportTopicsBulkRequest, db: Session = Depends(get_db)):

    # Step 1: Fetch all master topics
    topics = db.query(CudosTopic).filter(
        CudosTopic.academic_batch_id == request.academic_batch_id,
        CudosTopic.semester_id == request.semester_id,
        CudosTopic.course_id == request.course_id
    ).all()

    if not topics:
        return {"message": "No topics found in master"}

    imported_count = 0

    for topic in topics:

        exists = db.query(LMSMapInstructorTopic).filter(
            LMSMapInstructorTopic.academic_batch_id == request.academic_batch_id,
            LMSMapInstructorTopic.semester_id == request.semester_id,
            LMSMapInstructorTopic.crs_id == request.course_id,
            LMSMapInstructorTopic.section_id == request.section_id,
            LMSMapInstructorTopic.topic_id == topic.topic_id
        ).first()

        if not exists:
            new_map = LMSMapInstructorTopic(
                academic_batch_id=request.academic_batch_id,
                semester_id=request.semester_id,
                crs_id=request.course_id,
                section_id=request.section_id,
                topic_id=topic.topic_id,
                instructor_id=request.instructor_id,
                created_by=request.created_by,
                created_date=datetime.now()
            )

            db.add(new_map)
            imported_count += 1

    db.commit()

    if imported_count == 0:
        return {"message": "All topics already imported"}

    return {
        "message": "Import completed successfully",
        "imported_count": imported_count
    }


# ==============================
# API 10 – Imported Topic List to LMS mapping with Full Details
# API – Imported Topic Full Details
# ==============================
@router.post("/imported_topic_list")
def imported_topic_list(request: TopicListRequest, db: Session = Depends(get_db)):

    results = db.query(
        LMSMapInstructorTopic,
        CudosTopic,
        TopicLessonSchedule,
        LMSMapPortionLS
    ).join(
        CudosTopic,
        LMSMapInstructorTopic.topic_id == CudosTopic.topic_id
    ).outerjoin(
        TopicLessonSchedule,
        TopicLessonSchedule.topic_id == CudosTopic.topic_id
    ).outerjoin(
        LMSMapPortionLS,
        LMSMapPortionLS.topic_id == CudosTopic.topic_id
    ).filter(
        LMSMapInstructorTopic.academic_batch_id == request.academic_batch_id,
        LMSMapInstructorTopic.semester_id == request.semester_id,
        LMSMapInstructorTopic.crs_id == request.course_id
    ).all()

    response = []

    for mapping, topic, schedule, portion in results:
        response.append({
            "topic_id": topic.topic_id,
            "topic_code": topic.topic_code,
            "topic_title": topic.topic_title,
            "section_id": mapping.section_id,
            "instructor_id": mapping.instructor_id,

            # lesson schedule details
            "conduction_date": schedule.conduction_date if schedule else None,
            "actual_delivery_date": schedule.actual_delivery_date if schedule else None,

            # portion mapping details
            "portion_id": portion.portion_id if portion else None,
            "marks_expt": portion.marks_expt if portion else None
        })

    return response

# ==============================
# 2API 11– Edit Topic & Lesson Schedule(task2 apis))
# ==============================
@router.put("/edit_topic_schedule")
def edit_topic_schedule(request: EditTopicScheduleRequest, db: Session = Depends(get_db)):

    # Step 1: Get mapping
    mapping = db.query(LMSMapInstructorTopic).filter(
        LMSMapInstructorTopic.inst_map_id == request.inst_map_id
    ).first()

    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")

    # Step 2: Get schedule using topic_id
    schedule = db.query(TopicLessonSchedule).filter(
        TopicLessonSchedule.topic_id == mapping.topic_id
    ).first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Step 3: Update schedule
    schedule.conduction_date = request.conduction_date
    schedule.actual_delivery_date = request.actual_delivery_date
    schedule.marks_expt = request.marks_expt
    schedule.modified_by = request.modified_by
    schedule.modified_date = datetime.utcnow()

    db.commit()

    return {"message": "Topic schedule updated successfully"}

# ==============================
# API 12 – Add Extra Topic
# ==============================

@router.post("/add_extra_topic")
def add_extra_topic(request: AddExtraTopicRequest, db: Session = Depends(get_db)):

    # Insert into instructor topic mapping table
    new_mapping = LMSMapInstructorTopic(
        academic_batch_id=request.academic_batch_id,
        semester_id=request.semester_id,
        crs_id=request.course_id,
        section_id=request.section_id,
        topic_id=request.topic_id,
        instructor_id=request.instructor_id,
        created_by=request.created_by
    )

    db.add(new_mapping)
    db.commit()
    db.refresh(new_mapping)

    # Insert into lesson schedule table
    lesson = TopicLessonSchedule(
    academic_batch_id=request.academic_batch_id,
    semester_id=request.semester_id,
    course_id=request.course_id,
    topic_id=request.topic_id,
    portion_ref="1",
    portion_per_hour="1",
    created_by=request.created_by
)

    db.add(lesson)
    db.commit()

    return {
        "message": "Extra topic added successfully",
        "inst_map_id": new_mapping.inst_map_id
    }


# ==============================
# 2API 13– Instructor List
# ==============================
@router.get("/instructor_list")
def instructor_list(db: Session = Depends(get_db)):

    instructors = db.query(LMSMapInstructorTopic).all()

    return instructors
