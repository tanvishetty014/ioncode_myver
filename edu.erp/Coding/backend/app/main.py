from fastapi import FastAPI, Request, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import date, datetime, timedelta
import time

# Internal imports from your project structure
from .api.v1.routes import router as api_router
from .db.models import Base  
from .core.database import engine, SessionLocal 
from sqlalchemy.orm import Session
from sqlalchemy import text  
from pydantic import BaseModel

# --- EXISTING SCHEMAS (DO NOT CHANGE) ---
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
    status: str 
    date: date
    course_id: int

# --- UPDATED SCHEMAS FOR TIMETABLE ---
# Changed types to 'str' to handle frontend date inputs more flexibly 
# and avoid 422 errors during Pydantic validation.
class CopyDayRequest(BaseModel):
    tt_detail_id: int
    source_date: str 
    target_date: str
    user_id: int

class ResetTimetableRequest(BaseModel):
    tt_detail_id: int
    new_start_date: str

class UpdateRangeRequest(BaseModel):
    tt_detail_id: int
    new_end_date: str
    user_id: int

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to IonCudos API", "status": "Online"}

# --- HIERARCHY, QUIZ, & STATUS APIs (Teammate work - kept identical) ---
@app.get("/api/v1/hierarchy/programs", response_model=List[DropdownResponse])
def get_programs(dept_id: int, db: Session = Depends(get_db)):
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

@app.get("/api/v1/quizzes/scheduled", response_model=List[QuizListSchema])
def list_scheduled_quizzes(course_id: int, section_id: int, db: Session = Depends(get_db)):
    return [{"quiz_id": 10, "title": "Mid-Term Python", "scheduled_date": datetime.now()}]

@app.get("/api/v1/quizzes/results", response_model=List[StudentMarkSchema])
def get_quiz_results(quiz_id: int, section_id: int, db: Session = Depends(get_db)):
    return [{"student_name": "Alice", "roll_no": "CS01", "secured_marks": 45.5, "status": "Submitted"}]

@app.get("/api/v1/classes/dates")
def get_scheduled_dates(course_id: int, section_id: int, db: Session = Depends(get_db)):
    today = date.today()
    return {"selected_date": today, "available_dates": [today.isoformat()]}

# =================================================================
# FIXED TIMETABLE LOGIC APIS (YOUR TASK)
# =================================================================

# 1. API for Copy Class Day
@app.post("/api/v1/timetable/copy-day")
def copy_class_day(req: CopyDayRequest, db: Session = Depends(get_db)):
    """Copies all classes from source_date to target_date for a specific timetable."""
    # We select from mapping to duplicate existing instances to a new date
    copy_script = text("""
        INSERT INTO lms_tt_time_table_day_mapping 
            (time_table_id, tt_detail_id, day_id, week_day_name, class_date, allot_crs_id, extra_class_flag, created_by)
        SELECT 
            time_table_id, tt_detail_id, day_id, week_day_name, :target, allot_crs_id, 2, :user
        FROM lms_tt_time_table_day_mapping
        WHERE class_date = :source AND tt_detail_id = :tt_id
    """)
    result = db.execute(copy_script, {"target": req.target_date, "source": req.source_date, "tt_id": req.tt_detail_id, "user": req.user_id})
    db.commit()
    
    if result.rowcount == 0:
        return {"message": "No classes found on source date to copy"}
    return {"message": "Day copied successfully", "count": result.rowcount}

# 2. API for Delete Timetable (FIXED 422 Error: accepts class_date as str)
@app.delete("/api/v1/timetable/delete-day")
def delete_timetable_day(tt_detail_id: int, class_date: str, db: Session = Depends(get_db)):
    """Deletes all class mappings for a single day."""
    # Accepting class_date as a string prevents Pydantic from failing if the 
    # frontend sends a format it doesn't strictly recognize as a 'date' object.
    delete_script = text("""
        DELETE FROM lms_tt_time_table_day_mapping 
        WHERE tt_detail_id = :tt_id AND class_date = :c_date
    """)
    result = db.execute(delete_script, {"tt_id": tt_detail_id, "c_date": class_date})
    db.commit()
    return {"message": f"Timetable for {class_date} deleted", "deleted_count": result.rowcount}

# 3. API for Reset Timetable Date (Shifting the start date)
@app.put("/api/v1/timetable/reset-date")
def reset_timetable_date(req: ResetTimetableRequest, db: Session = Depends(get_db)):
    """Shifts all classes based on a new start date."""
    res = db.execute(text("SELECT tt_start_date FROM lms_tt_time_table_details WHERE tt_detail_id = :id"), {"id": req.tt_detail_id}).fetchone()
    if not res or not res[0]: 
        raise HTTPException(status_code=404, detail="Timetable not found")
    
    try:
        # DB might store as VARCHAR, ensure it's a string before parsing
        old_start_str = str(res[0])
        old_start = datetime.strptime(old_start_str, '%Y-%m-%d').date()
        new_start = datetime.strptime(req.new_start_date, '%Y-%m-%d').date()
        delta = (new_start - old_start).days
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD")

    # Update all dates in mapping by the difference (delta)
    shift_script = text("""
        UPDATE lms_tt_time_table_day_mapping 
        SET class_date = DATE_ADD(STR_TO_DATE(class_date, '%Y-%m-%d'), INTERVAL :days DAY)
        WHERE tt_detail_id = :tt_id
    """)
    db.execute(shift_script, {"days": delta, "tt_id": req.tt_detail_id})
    
    # Update the main detail table
    db.execute(text("UPDATE lms_tt_time_table_details SET tt_start_date = :d WHERE tt_detail_id = :id"), 
               {"d": req.new_start_date, "id": req.tt_detail_id})
    
    db.commit()
    return {"message": "Timetable dates shifted successfully", "days_shifted": delta}

# 4. API for Add/Delete classes based on date reduced or increased
@app.put("/api/v1/timetable/update-range")
def update_timetable_range(req: UpdateRangeRequest, db: Session = Depends(get_db)):
    """If end_date is reduced, delete classes. If increased, add classes based on weekly template."""
    res = db.execute(text("SELECT tt_end_date FROM lms_tt_time_table_details WHERE tt_detail_id = :id"), {"id": req.tt_detail_id}).fetchone()
    
    if not res or not res[0]:
        raise HTTPException(status_code=404, detail="Timetable record not found")

    try:
        old_end = datetime.strptime(str(res[0]), '%Y-%m-%d').date()
        new_end = datetime.strptime(req.new_end_date, '%Y-%m-%d').date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Check date formats (YYYY-MM-DD)")

    if new_end < old_end:
        # REDUCED: Delete classes outside new range
        db.execute(text("DELETE FROM lms_tt_time_table_day_mapping WHERE tt_detail_id = :id AND class_date > :new_end"), 
                   {"id": req.tt_detail_id, "new_end": req.new_end_date})
    
    elif new_end > old_end:
        # INCREASED: Add classes from template for new days
        current_date = old_end + timedelta(days=1)
        while current_date <= new_end:
            # Python weekday (0=Mon, 6=Sun) -> your day_id (1=Mon, 7=Sun)
            target_day_id = current_date.weekday() + 1 
            
            fill_script = text("""
                INSERT INTO lms_tt_time_table_day_mapping 
                (time_table_id, tt_detail_id, day_id, week_day_name, class_date, allot_crs_id, created_by)
                SELECT time_table_id, tt_detail_id, day_id, week_day_name, :c_date, crs_id, :user
                FROM lms_tt_time_table 
                WHERE tt_detail_id = :tt_id AND day_id = :d_id
            """)
            db.execute(fill_script, {
                "c_date": current_date.strftime('%Y-%m-%d'), 
                "user": req.user_id, 
                "tt_id": req.tt_detail_id, 
                "d_id": target_day_id
            })
            current_date += timedelta(days=1)

    # Update main table end date
    db.execute(text("UPDATE lms_tt_time_table_details SET tt_end_date = :d WHERE tt_detail_id = :id"), 
               {"d": req.new_end_date, "id": req.tt_detail_id})
    db.commit()
    return {"message": "Timetable range updated successfully"}