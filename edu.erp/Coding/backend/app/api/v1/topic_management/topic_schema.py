# ============================================================
# TOPIC MANAGEMENT SCHEMAS
# ============================================================

from pydantic import BaseModel
from typing import Optional
from datetime import date as date_type


# Request schema for fetching courses based on curriculum and term
# Used in: course_list API endpoint
class CourseListRequest(BaseModel):
    curriculum_id: int
    term_id: int


# Request schema for fetching sections based on program and semester
# Used in: section_list API endpoint
class TopicSectionListRequest(BaseModel):
    program_id: int
    semester: int


# Request schema for importing a topic (with optional fields)
# Used in: import_topic API endpoint
class ImportTopicRequest(BaseModel):
    topic_code: Optional[str]
    topic_title: str
    topic_content: Optional[str]
    academic_batch_id: int
    semester_id: int
    course_id: int
    created_by: int


# Request schema for creating a new topic
# Used in: import_topic, update_topic API endpoints
class TopicCreateRequest(BaseModel):
    topic_code: str
    topic_title: str
    topic_content: str
    academic_batch_id: int
    semester_id: int
    course_id: int
    created_by: int


# Request schema for listing topics by academic batch, semester and course
# Used in: topic_list, imported_topic_list API endpoints
class TopicListRequest(BaseModel):
    academic_batch_id: int
    semester_id: int
    course_id: int


# Request schema for bulk importing topics to LMS mapping
# Used in: import_topics_bulk API endpoint
class ImportTopicsBulkRequest(BaseModel):
    academic_batch_id: int
    semester_id: int
    course_id: int
    section_id: int
    instructor_id: int
    created_by: int


# Request schema for editing topic schedule details
# Used in: edit_topic_schedule API endpoint
class EditTopicScheduleRequest(BaseModel):
    inst_map_id: int
    conduction_date: Optional[date_type]
    actual_delivery_date: Optional[date_type]
    marks_expt: Optional[int]
    modified_by: int


# Request schema for adding an extra topic to LMS mapping
# Used in: add_extra_topic API endpoint
class AddExtraTopicRequest(BaseModel):
    topic_id: int
    academic_batch_id: int
    semester_id: int
    course_id: int
    section_id: int
    instructor_id: int
    topic_hrs: Optional[str] = None
    num_of_sessions: Optional[float] = None
    created_by: int

