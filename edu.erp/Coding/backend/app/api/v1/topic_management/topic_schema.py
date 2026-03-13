from pydantic import BaseModel
from typing import Optional, List

class CurriculumListRequest(BaseModel):
    pass  # No parameters needed

class SemesterListRequest(BaseModel):
    pass  # No parameters needed

class CourseListRequest(BaseModel):
    curriculum_id: Optional[int] = None
    semester_id: Optional[int] = None

class TopicSectionListRequest(BaseModel):
    course_id: int
    semester_id: int

class ImportTopicRequest(BaseModel):
    academic_batch_id: int
    semester_id: int
    course_id: int
    section_id: int
    created_by: int = 1

class TopicCreateRequest(BaseModel):
    topic_code: str
    topic_title: str
    topic_content: Optional[str] = None
    academic_batch_id: int
    semester_id: int
    course_id: int
    created_by: int
    
class TopicListRequest(BaseModel):
    course_id: int
    semester_id: int
    section_id: Optional[int] = None


# ✅ Instructor list schema
class InstructorListRequest(BaseModel):
    course_id: int


# ✅ Import selected topics
class ImportCudosTopicsRequest(BaseModel):
    course_id: int
    semester_id: int
    section_id: int
    topic_ids: List[int]
    instructor_id: int
    academic_batch_id: int
    created_by: int = 1


# ✅ Topic schedule request
class TopicScheduleRequest(BaseModel):
    mapping_id: int

# ✅ Update instructor for a topic  
class UpdateInstructorRequest(BaseModel):
    course_instructor_id: int