from fastapi import FastAPI, Request, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import date, datetime
import time

# Internal imports from your project structure
from .api.v1.routes import router as api_router
from .db.models import Base  # Ensure your models like Department, Quiz, etc., are here
from .core.database import engine, SessionLocal 
from sqlalchemy.orm import Session
from pydantic import BaseModel

# --- NEW: Pydantic Schemas (Defining the data structure) ---
class DropdownResponse(BaseModel):
    id: int
    name: str

class QuizListSchema(BaseModel):
    quiz_id: int
    title: str
    scheduled_date: datetime

class StudentMarkSchema(BaseModel):
    student_name: str
    roll_no: str
    secured_marks: Optional[float]
    status: str

class AttendanceStatusSchema(BaseModel):
    status: str  # class not scheduled, attendance not taken, inprogress, finalized
    date: date
    course_id: int

app = FastAPI()

# --- Database Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Existing Middleware ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    print(f"REQUEST: {request.method} {request.url.path} - STATUS: {response.status_code} - TIME: {process_time:.2f}ms")
    return response

# Configuration for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the main API router
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to IonCudos API", "status": "Online"}


# =================================================================
# NEW TASK APIS START HERE
# =================================================================

# 1. HIERARCHY APIs
@app.get("/api/v1/hierarchy/programs", response_model=List[DropdownResponse])
def get_programs(dept_id: int, db: Session = Depends(get_db)):
    # Logic: return db.query(models.Program).filter(models.Program.dept_id == dept_id).all()
    return [{"id": 1, "name": "B.E Computer Science"}]

@app.get("/api/v1/hierarchy/curriculum", response_model=List[DropdownResponse])
def get_curriculum(dept_id: int, db: Session = Depends(get_db)):
    return [{"id": 1, "name": "2023 Regulation"}]

@app.get("/api/v1/hierarchy/terms", response_model=List[DropdownResponse])
def get_terms(curriculum_id: int, db: Session = Depends(get_db)):
    return [{"id": 4, "name": "Semester 4"}]

@app.get("/api/v1/hierarchy/sections", response_model=List[DropdownResponse])
def get_sections(term_id: int, db: Session = Depends(get_db)):
    return [{"id": 101, "name": "Section A"}]


# 2. QUIZ APIs
@app.get("/api/v1/quizzes/scheduled", response_model=List[QuizListSchema])
def list_scheduled_quizzes(course_id: int, section_id: int, db: Session = Depends(get_db)):
    # Logic: Filter Quiz table by course and section
    return [{"quiz_id": 10, "title": "Mid-Term Python", "scheduled_date": datetime.now()}]

@app.get("/api/v1/quizzes/results", response_model=List[StudentMarkSchema])
def get_quiz_results(quiz_id: int, section_id: int, db: Session = Depends(get_db)):
    # Logic: Join Student and Marks tables
    return [
        {"student_name": "Alice", "roll_no": "CS01", "secured_marks": 45.5, "status": "Submitted"},
        {"student_name": "Bob", "roll_no": "CS02", "secured_marks": 0.0, "status": "Absent"}
    ]


# 3. CLASS SCHEDULE & ATTENDANCE STATUS APIs
@app.get("/api/v1/classes/dates")
def get_scheduled_dates(course_id: int, section_id: int, db: Session = Depends(get_db)):
    """Fetch scheduled dates. Default today's date is returned as selected."""
    today = date.today()
    # Logic: fetch distinct dates from your ClassSchedule table
    return {
        "selected_date": today,
        "available_dates": [today.isoformat(), "2024-05-20", "2024-05-22"]
    }

@app.get("/api/v1/classes/status", response_model=AttendanceStatusSchema)
def fetch_attendance_status(
    course_id: int, 
    section_id: int, 
    scheduled_date: date = Query(default=date.today()), 
    db: Session = Depends(get_db)
):
    """
    Logic:
    1. Check if class exists in Schedule Table -> If no: "class not scheduled"
    2. Check if row exists in Attendance Table -> If no: "attendance not taken"
    3. Check 'is_finalized' flag -> "inprogress" or "finalized"
    """
    # This is dummy logic - replace with your actual DB queries
    class_exists = True 
    attendance_exists = True
    is_finalized = False

    if not class_exists:
        current_status = "class not scheduled"
    elif not attendance_exists:
        current_status = "attendance not taken"
    else:
        current_status = "finalized" if is_finalized else "inprogress"

    return {
        "status": current_status,
        "date": scheduled_date,
        "course_id": course_id
    }