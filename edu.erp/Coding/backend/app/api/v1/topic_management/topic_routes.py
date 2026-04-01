from urllib import request

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import distinct, text
from datetime import date, datetime
from typing import Optional

from app.core.database import get_db
# Strictly using ONLY the allowed tables from your models.py
from app.db.models import (
    IEMSCourses,
    IEMSection,
    CudosTopic,
    IEMSAcademicBatch,
    IEMSemester,
    LMSMapInstructorTopic,
    TopicLessonSchedule,
    LMSMapPortionLS,
    IEMSUsers,
    CudosMapCourseToCourseInstructor  # Added back for the Instructor/Handled By column
)
# Using only your pre-existing schemas
from .topic_schema import (
    CourseListRequest,
    TopicCreateRequest,
    TopicListRequest,
    UpdateInstructorRequest
)
from app.api.v1.ems_module.comman_functions.comman_function import (
    get_topics as comman_get_topics,
    map_lesson as comman_map_lesson,
)

router = APIRouter(tags=["Topic Management"])

# Helper function to return success response
def success_response(data, message="Success"):
    return {
        "status": True,
        "message": message,
        "data": data
    }

# Helper function to return error response
def error_response(message, data=None):
    return {
        "status": False,
        "message": message,
        "data": data
    }

# =========================================================
# ✅ DROPDOWN APIs
# =========================================================

@router.post("/topic/curriculum_list")
def get_curriculum_list_post(db: Session = Depends(get_db)):
    try:
        data = db.query(IEMSAcademicBatch).all()
        result = [
            {
                "value": row.academic_batch_id,
                "label": f"{row.academic_batch_desc} ({row.academic_year})",
            }
            for row in data
        ]
        return success_response(result)
    except Exception as e:
        print(f"ERROR in curriculum_list: {e}")
        return error_response(str(e))

@router.post("/topic/semester_list")
def get_semester_list_post(db: Session = Depends(get_db)):
    try:
        data = db.query(IEMSemester).all()
        result = [
            {
                "value": row.semester_id,
                "label": f"Semester {row.semester}" if row.semester else row.semester_desc,
            }
            for row in data
        ]
        return success_response(result)
    except Exception as e:
        print(f"ERROR in semester_list: {e}")
        return error_response(str(e))

@router.post("/topic/course_list")
def get_course_list(request: CourseListRequest, db: Session = Depends(get_db)):
    """Get all courses - returns courses for selected curriculum"""
    try:
        query = db.query(IEMSCourses)
        
        # Filter by curriculum only
        if request.curriculum_id:
            query = query.filter(IEMSCourses.academic_batch_id == request.curriculum_id)
        
        courses = query.all()
        
        if not courses:
            return success_response([])
            
        result = [
            {
                "value": row.crs_id,
                "label": row.crs_title or f"Course {row.crs_id}",
                "crs_id": row.crs_id,
                "crs_code": row.crs_code,
                "crs_title": row.crs_title,
                "semester": row.semester,
            }
            for row in courses
        ]
        return success_response(result)
    except Exception as e:
        print(f"ERROR in course_list: {e}")
        return error_response(str(e))


@router.post("/topic/section_list_post")
def get_section_list(
    course_id: Optional[int] = Body(None),
    semester_id: Optional[int] = Body(None),
    academic_batch_id: Optional[int] = Body(None),
    db: Session = Depends(get_db)
):
    """Get sections strictly from the allowed IEMSection table (No extra BaseModel required)"""
    try:
        query = db.query(IEMSection)

        if academic_batch_id:
            query = query.filter(IEMSection.academic_batch_id == academic_batch_id)
        if semester_id:
            query = query.filter(IEMSection.semester_id == semester_id)

        sections = query.all()

        if sections:
            return [
                {
                    "value": s.id,
                    "label": s.section or f"Section {s.id}",
                }
                for s in sections
            ]

        # Fallback: return default sections and add them to IEMSection if they don't exist
        default_sections = ["A", "B", "C", "D"]
        result = []
        for section_name in default_sections:
            existing_section = db.query(IEMSection).filter(
                IEMSection.section == section_name
            ).first()

            if existing_section:
                result.append({
                    "value": existing_section.id,
                    "label": existing_section.section
                })
            else:
                new_section = IEMSection(
                    section=section_name,
                    academic_batch_id=academic_batch_id,
                    semester_id=semester_id,
                    status=1
                )
                db.add(new_section)
                db.flush()
                result.append({
                    "value": new_section.id,
                    "label": section_name
                })

        db.commit()
        return result

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# =========================================================
# ✅ IMPORT & LISTING
# =========================================================

@router.post("/topic/import_topic")
def import_topic(
    academic_batch_id: int = Body(...),
    semester_id: int = Body(...),
    course_id: int = Body(...),
    section_id: int = Body(...),
    created_by: int = Body(1),
    db: Session = Depends(get_db)
):
    """Import topics from cudos_topic to lms_map_instructor_topic (No extra BaseModel required)"""
    try:
        print(f"DEBUG: Import request - academic_batch_id={academic_batch_id}, course_id={course_id}, semester_id={semester_id}, section_id={section_id}")

        # Get ALL topics for this course and semester from cudos_topic
        master_topics = db.query(CudosTopic).filter(
            CudosTopic.semester_id == semester_id,
            CudosTopic.course_id == course_id
        ).all()

        print(f"DEBUG: Found {len(master_topics)} topics for course_id={course_id}, semester_id={semester_id}")

        if not master_topics:
            return {"status": "error", "message": "No topics found in master source (cudos_topic)"}

        imported_count = 0
        for topic in master_topics:
            exists = db.query(LMSMapInstructorTopic).filter(
                LMSMapInstructorTopic.topic_id == topic.topic_id,
                LMSMapInstructorTopic.crs_id == course_id,
                LMSMapInstructorTopic.section_id == section_id
            ).first()

            if not exists:
                new_mapping = LMSMapInstructorTopic(
                    academic_batch_id=academic_batch_id,
                    semester_id=semester_id,
                    crs_id=course_id,
                    section_id=section_id,
                    topic_id=topic.topic_id,
                    created_by=created_by
                )
                db.add(new_mapping)
                imported_count += 1
                print(f"DEBUG: Imported topic {topic.topic_id} - {topic.topic_title}")

        db.commit()

        print(f"DEBUG: Import completed, {imported_count} new topics imported")

        if imported_count == 0:
            return {"status": "success", "message": "All topics already imported"}

        return {"status": "success", "message": f"Successfully imported {imported_count} new topics"}

    except Exception as e:
        db.rollback()
        print(f"DEBUG: Import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/topic/topic_list")
def topic_list(request: TopicListRequest, db: Session = Depends(get_db)):
    """List ALL topics for this course/semester from cudos_topic, with import status"""
    try:
        # Get ALL topics for this course and semester from cudos_topic
        topics = db.query(CudosTopic).filter(
            CudosTopic.course_id == request.course_id,
            CudosTopic.semester_id == request.semester_id
        ).all()

        print(f"DEBUG: Found {len(topics)} topics in cudos_topic for course_id={request.course_id}, semester_id={request.semester_id}")

        if not topics:
            return success_response([])

        # Get imported mappings for this course/section
        mappings = {}
        if request.section_id:
            imported_mappings = db.query(LMSMapInstructorTopic).filter(
                LMSMapInstructorTopic.crs_id == request.course_id,
                LMSMapInstructorTopic.semester_id == request.semester_id,
                LMSMapInstructorTopic.section_id == request.section_id
            ).all()
            mappings = {m.topic_id: m for m in imported_mappings}

        response = []
        for topic in topics:
            mapping = mappings.get(topic.topic_id)
            
            # Get instructor name if imported
            instructor_name = "Not Assigned"
            instructor_id = None
            if mapping and mapping.instructor_id:
                instructor = db.query(IEMSUsers).filter(
                    IEMSUsers.id == mapping.instructor_id
                ).first()
                if instructor:
                    first_name = getattr(instructor, 'first_name', '') or ''
                    last_name = getattr(instructor, 'last_name', '') or ''
                    full_name = f"{first_name} {last_name}".strip()
                    if full_name:
                        instructor_name = full_name
                        instructor_id = mapping.instructor_id

            # Get schedule details if imported
            schedule = None
            if mapping:
                schedule = db.query(TopicLessonSchedule).filter(
                    TopicLessonSchedule.topic_id == topic.topic_id
                ).first()

            # Get portion details and lesson schedule
            portion_list_query = db.execute(text("""
                SELECT portion_ref FROM lms_map_portion_ls 
                WHERE topic_id = :topic_id AND portion_ref IS NOT NULL AND portion_ref != ''
            """), {"topic_id": topic.topic_id})
            portion_refs = [r[0] for r in portion_list_query.fetchall() if r[0]]
            lesson_schedule = ", ".join(portion_refs) if portion_refs else None

            # Get marks_expt (handle if column doesn't exist)
            try:
                portion_query = db.execute(text("""
                    SELECT marks_expt FROM lms_map_portion_ls 
                    WHERE topic_id = :topic_id LIMIT 1
                """), {"topic_id": topic.topic_id})
                portion_row = portion_query.fetchone()
                marks_expt = portion_row[0] if portion_row else None
            except Exception as e:
                print(f"Warning: Could not get marks_expt for topic {topic.topic_id}: {e}")
                marks_expt = None

            response.append({
                "topic_id": topic.topic_id,
                "mapping_id": mapping.inst_map_id if mapping else None,
                "inst_map_id": mapping.inst_map_id if mapping else None,
                "topic_code": topic.topic_code,
                "topic_title": topic.topic_title,
                "topic_content": topic.topic_content,
                "topic_hrs": topic.topic_hrs,
                "num_of_sessions": topic.num_of_sessions,
                "section_id": request.section_id,
                "instructor_id": instructor_id,
                "instructor_name": instructor_name,
                "lesson_schedule": lesson_schedule,
                "conduction_date": schedule.conduction_date.isoformat() if schedule and schedule.conduction_date else None,
                "actual_delivery_date": schedule.actual_delivery_date.isoformat() if schedule and schedule.actual_delivery_date else None,
                "marks_expt": marks_expt,
                "is_imported": mapping is not None  # Add flag to indicate import status
            })
        
        print(f"DEBUG: Returning {len(response)} topics")
        return success_response(response)

    except Exception as e:
        print(f"DEBUG: Error in topic_list: {e}")
        return error_response(str(e))

# -----------------------------
# UPDATE — Topic
# -----------------------------
@router.put("/topic/update_topic/{topic_id}")
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
        topic.modified_date = date.today()

        db.commit()
        db.refresh(topic)

        return {"message": "Topic updated successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# DELETE — Topic
# -----------------------------
@router.delete("/topic/delete_topic/{topic_id}")
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


# =========================================================
# ✅ NEW ENDPOINTS FOR MANAGE TOPIC INSTRUCTOR
# =========================================================

# -----------------------------
# GET INSTRUCTOR LIST
# -----------------------------
@router.post("/topic/instructor_list")
def instructor_list(db: Session = Depends(get_db)):
    try:

        instructors = db.query(
            CudosMapCourseToCourseInstructor.course_instructor_id,
            IEMSUsers.first_name,
            IEMSUsers.last_name
        ).join(
            IEMSUsers,
            IEMSUsers.id == CudosMapCourseToCourseInstructor.course_instructor_id
        ).all()

        return [
            {
                "value": inst.course_instructor_id,
                "label": f"{inst.first_name} {inst.last_name}"
            }
            for inst in instructors
        ]

    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=str(e))
# -----------------------------
# UPDATE INSTRUCTOR
# -----------------------------
@router.put("/topic/update_instructor/{mapping_id}")
def update_instructor(
    mapping_id: int,
    request: UpdateInstructorRequest,
    db: Session = Depends(get_db)
):

    print("Mapping ID:", mapping_id)
    print("Instructor ID:", request.course_instructor_id)    

    mapping = db.query(LMSMapInstructorTopic).filter(
        LMSMapInstructorTopic.inst_map_id == mapping_id
    ).first()

    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")

    mapping.instructor_id = request.course_instructor_id

    db.commit()
    db.refresh(mapping)

    return {
        "status": True,
        "message": "Instructor updated successfully"
    }
# -----------------------------
# GET CUDOS TOPICS (Not yet imported)
# -----------------------------
@router.post("/topic/cudos_topics")
def get_cudos_topics(
    course_id: int = Body(...),
    semester_id: int = Body(...),
    section_id: int = Body(...),
    db: Session = Depends(get_db)
):
    """Get topics from cudos_topic that are NOT yet imported for this course/section"""
    try:
        # Get all topic IDs already imported for this course and section
        imported_topic_ids = db.query(LMSMapInstructorTopic.topic_id).filter(
            LMSMapInstructorTopic.crs_id == course_id,
            LMSMapInstructorTopic.section_id == section_id
        ).all()
        
        imported_ids = [t.topic_id for t in imported_topic_ids]
        
        # Get topics from cudos_topic that are NOT imported
        query = db.query(CudosTopic).filter(
            CudosTopic.course_id == course_id,
            CudosTopic.semester_id == semester_id
        )
        
        if imported_ids:
            query = query.filter(~CudosTopic.topic_id.in_(imported_ids))
        
        topics = query.all()
        
        return [
            {
                "topic_id": t.topic_id,
                "topic_code": t.topic_code,
                "topic_title": t.topic_title,
                "topic_hrs": t.topic_hrs,
                "num_of_sessions": t.num_of_sessions
            }
            for t in topics
        ]
    except Exception as e:
        print(f"DEBUG: Error in cudos_topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# IMPORT SELECTED CUDOS TOPICS WITH INSTRUCTOR
# -----------------------------
@router.post("/topic/import_cudos_topics")
def import_cudos_topics(
    course_id: int = Body(...),
    semester_id: int = Body(...),
    section_id: int = Body(...),
    topic_ids: list = Body(...),
    instructor_id: int = Body(...),
    academic_batch_id: int = Body(...),
    created_by: int = Body(1),
    db: Session = Depends(get_db)
):
    """Import selected topics from cudos_topic with instructor assignment"""
    try:
        imported_count = 0
        
        for topic_id in topic_ids:
            # Check if already imported
            exists = db.query(LMSMapInstructorTopic).filter(
                LMSMapInstructorTopic.topic_id == topic_id,
                LMSMapInstructorTopic.crs_id == course_id,
                LMSMapInstructorTopic.section_id == section_id
            ).first()
            
            if not exists:
                new_mapping = LMSMapInstructorTopic(
                    academic_batch_id=academic_batch_id,
                    semester_id=semester_id,
                    crs_id=course_id,
                    section_id=section_id,
                    topic_id=topic_id,
                    instructor_id=instructor_id,
                    created_by=created_by
                )
                db.add(new_mapping)
                imported_count += 1
        
        db.commit()
        
        if imported_count == 0:
            return {"status": "success", "message": "All selected topics already imported"}
        
        return {"status": "success", "message": f"Successfully imported {imported_count} topics"}
    
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Error in import_cudos_topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# GET TOPIC SCHEDULES
# -----------------------------
@router.post("/topic/topic_schedules")
def get_topic_schedules(
    mapping_id: int = Body(...),
    db: Session = Depends(get_db)
):
    """Get lesson schedules for a specific topic mapping"""
    try:
        # Get the mapping to find the topic_id
        mapping = db.query(LMSMapInstructorTopic).filter(
            LMSMapInstructorTopic.inst_map_id == mapping_id
        ).first()
        
        if not mapping:
            raise HTTPException(status_code=404, detail="Topic mapping not found")
        
        # Get schedules for this topic (from topic_lesson_schedule + lms_map_portion_ls for portion_ref)
        from sqlalchemy import text
        schedules = db.query(TopicLessonSchedule).filter(
            TopicLessonSchedule.topic_id == mapping.topic_id
        ).order_by(TopicLessonSchedule.lesson_schedule_id).all()

        # Get all portions for this topic (portion_ref) - match by index with schedules
        portion_refs = []
        try:
            portion_rows = db.execute(text("""
                SELECT portion_ref FROM lms_map_portion_ls 
                WHERE topic_id = :topic_id AND portion_ref IS NOT NULL AND portion_ref != ''
                ORDER BY portion_id
            """), {"topic_id": mapping.topic_id}).fetchall()
            portion_refs = [r[0] for r in portion_rows if r[0]]
        except Exception:
            pass

        result = []
        for idx, s in enumerate(schedules):
            portion_ref = portion_refs[idx] if idx < len(portion_refs) else None
            result.append({
                "schedule_id": s.lesson_schedule_id,
                "topic_id": s.topic_id,
                "session_number": idx + 1,
                "portion_to_be_covered": portion_ref,
                "conduction_date": s.conduction_date.isoformat() if s.conduction_date else None,
                "actual_delivery_date": s.actual_delivery_date.isoformat() if s.actual_delivery_date else None,
            })
        return result
    except Exception as e:
        print(f"DEBUG: Error in topic_schedules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# UPDATE SCHEDULE
# -----------------------------
@router.put("/topic/update_schedule/{schedule_id}")
def update_schedule(
    schedule_id: int,
    conduction_date: str = Body(None),
    actual_delivery_date: str = Body(None),
    db: Session = Depends(get_db)
):
    """Update a lesson schedule"""
    try:
        schedule = db.query(TopicLessonSchedule).filter(
            TopicLessonSchedule.lesson_schedule_id == schedule_id
        ).first()
        
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        if conduction_date:
            schedule.conduction_date = datetime.strptime(conduction_date, '%Y-%m-%d').date()
        if actual_delivery_date:
            schedule.actual_delivery_date = datetime.strptime(actual_delivery_date, '%Y-%m-%d').date()
        
        db.commit()
        db.refresh(schedule)
        
        return {"status": "success", "message": "Schedule updated successfully"}
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Error in update_schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# ADD NEW SCHEDULE
# -----------------------------
@router.post("/topic/add_schedule")
def add_schedule(
    mapping_id: int = Body(...),
    session_number: int = Body(...),
    conduction_date: str = Body(None),
    created_by: int = Body(1),
    db: Session = Depends(get_db)
):
    """Add a new lesson schedule for a topic mapping"""
    try:
        # Get the mapping to find the topic_id
        mapping = db.query(LMSMapInstructorTopic).filter(
            LMSMapInstructorTopic.inst_map_id == mapping_id
        ).first()
        
        if not mapping:
            raise HTTPException(status_code=404, detail="Topic mapping not found")
        
        conduction_dt = None
        if conduction_date and str(conduction_date).strip():
            try:
                conduction_dt = datetime.strptime(str(conduction_date).strip(), '%Y-%m-%d').date()
            except ValueError:
                pass
        new_schedule = TopicLessonSchedule(
            topic_id=mapping.topic_id,
            conduction_date=conduction_dt,
            created_by=created_by
        )
        
        db.add(new_schedule)
        db.commit()
        db.refresh(new_schedule)
        
        return {
            "status": "success", 
            "message": "Schedule added successfully",
            "schedule_id": new_schedule.lesson_schedule_id
        }
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Error in add_schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# ADD EXTRA CLASS
# -----------------------------
@router.post("/topic/add_extra_class")
def add_extra_class(
    mapping_id: int = Body(...),
    class_date: str = Body(...),
    start_time: str = Body(None),
    end_time: str = Body(None),
    notes: str = Body(""),
    created_by: int = Body(1),
    db: Session = Depends(get_db)
):
    """Add an extra class for a topic mapping"""
    try:
        # Get the mapping to find the topic_id
        mapping = db.query(LMSMapInstructorTopic).filter(
            LMSMapInstructorTopic.inst_map_id == mapping_id
        ).first()
        
        if not mapping:
            raise HTTPException(status_code=404, detail="Topic mapping not found")
        
        class_dt = datetime.strptime(str(class_date).strip(), '%Y-%m-%d').date()
        new_schedule = TopicLessonSchedule(
            topic_id=mapping.topic_id,
            conduction_date=class_dt,
            actual_delivery_date=class_dt,
            created_by=created_by
        )
        
        db.add(new_schedule)
        db.commit()
        db.refresh(new_schedule)
        
        return {
            "status": "success",
            "message": "Extra class added successfully",
            "schedule_id": new_schedule.lesson_schedule_id
        }
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Error in add_extra_class: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# ADD NEW TOPIC
# -----------------------------
@router.post("/topic/add_new_topic")
def add_new_topic(
    academic_batch_id: int = Body(...),
    semester_id: int = Body(...),
    course_id: int = Body(...),
    section_id: int = Body(...),
    topic_title: str = Body(...),
    topic_code: str = Body(...),
    topic_content: str = Body(""),
    topic_hrs: str = Body(""),
    num_of_sessions: int = Body(1),
    instructor_id: int = Body(...),
    created_by: int = Body(1),
    db: Session = Depends(get_db)
):
    """Add a new topic to LMS tables (not to cudos_topic)"""
    try:
        # First, add to cudos_topic as well? No, the user said only LMS tables.
        # But to maintain consistency, perhaps add to cudos_topic first.
        # The requirements say "add more topics to these tables lms_map_instructor_topic, topic_lesson_schedule, lms_map_portion_ls"
        # So only LMS tables.
        
        # But cudos_topic has topic_id as primary key, so we need a topic_id.
        # Perhaps generate a new topic_id or use a dummy one.
        # To keep it simple, let's add to cudos_topic first to get a topic_id.
        
        new_topic = CudosTopic(
            topic_code=topic_code,
            topic_title=topic_title,
            topic_content=topic_content,
            topic_hrs=topic_hrs,
            num_of_sessions=num_of_sessions,
            academic_batch_id=academic_batch_id,
            semester_id=semester_id,
            course_id=course_id,
            created_by=created_by
        )
        db.add(new_topic)
        db.flush()  # To get the topic_id
        
        # Now add to LMS tables
        new_mapping = LMSMapInstructorTopic(
            academic_batch_id=academic_batch_id,
            semester_id=semester_id,
            crs_id=course_id,
            section_id=section_id,
            topic_id=new_topic.topic_id,
            instructor_id=instructor_id,
            created_by=created_by
        )
        db.add(new_mapping)
        
        # Add initial schedule
        new_schedule = TopicLessonSchedule(
            topic_id=new_topic.topic_id,
            created_by=created_by
        )
        db.add(new_schedule)
        
        db.commit()
        db.refresh(new_mapping)
        
        return {
            "status": "success",
            "message": "New topic added successfully",
            "topic_id": new_topic.topic_id,
            "mapping_id": new_mapping.inst_map_id
        }
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Error in add_new_topic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


router.add_api_route("/comman_function/map-lesson", comman_map_lesson, methods=["POST"])
router.add_api_route("/comman_function/topics", comman_get_topics, methods=["GET"])
