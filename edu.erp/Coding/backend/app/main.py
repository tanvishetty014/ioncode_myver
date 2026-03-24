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
from sqlalchemy import text  # Needed to run the SQL scripts
from pydantic import BaseModel

# --- NEW: Pydantic Schemas ---
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

# --- NEW: Schemas for Timetable Tasks ---
class CopyDayRequest(BaseModel):
    tt_detail_id: int
    source_date: date
    target_date: date
    user_id: int

class DeleteDayRequest(BaseModel):
    tt_detail_id: int
    class_date: date

class ResetTimetableRequest(BaseModel):
    tt_detail_id: int
    new_start_date: date

class UpdateRangeRequest(BaseModel):
    tt_detail_id: int
    new_end_date: date
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

# --- HIERARCHY, QUIZ, & STATUS APIs (Kept as per your code) ---
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
# NEW TIMETABLE LOGIC APIS (The Task)
# =================================================================

# 1. API for Copy Class Day
@app.post("/api/v1/timetable/copy-day")
def copy_class_day(req: CopyDayRequest, db: Session = Depends(get_db)):
    """Copies all classes from source_date to target_date for a specific timetable."""
    copy_script = text("""
        INSERT INTO lms_tt_time_table_day_mapping 
            (time_table_id, tt_detail_id, day_id, week_day_name, class_date, allot_crs_id, extra_class_flag, created_by)
        SELECT 
            time_table_id, tt_detail_id, day_id, week_day_name, :target, allot_crs_id, 2, :user
        FROM lms_tt_time_table_day_mapping
        WHERE class_date = :source AND tt_detail_id = :tt_id
    """)
    db.execute(copy_script, {"target": req.target_date, "source": req.source_date, "tt_id": req.tt_detail_id, "user": req.user_id})
    db.commit()
    return {"message": "Day copied successfully"}

# 2. API for Delete Timetable (Delete one specific day)
@app.delete("/api/v1/timetable/delete-day")
def delete_timetable_day(tt_detail_id: int, class_date: date, db: Session = Depends(get_db)):
    """Deletes all class mappings for a single day."""
    delete_script = text("""
        DELETE FROM lms_tt_time_table_day_mapping 
        WHERE tt_detail_id = :tt_id AND class_date = :c_date
    """)
    db.execute(delete_script, {"tt_id": tt_detail_id, "c_date": class_date})
    db.commit()
    return {"message": f"Timetable for {class_date} deleted"}

# 3. API for Reset Timetable Date (Shifting the start date)
@app.put("/api/v1/timetable/reset-date")
def reset_timetable_date(req: ResetTimetableRequest, db: Session = Depends(get_db)):
    """Shifts all classes based on a new start date."""
    # 1. Get current start date
    res = db.execute(text("SELECT tt_start_date FROM lms_tt_time_table_details WHERE tt_detail_id = :id"), {"id": req.tt_detail_id}).fetchone()
    if not res: raise HTTPException(status_code=404, detail="Timetable not found")
    
    old_start = datetime.strptime(res[0], '%Y-%m-%d').date()
    delta = (req.new_start_date - old_start).days

    # 2. Update all dates in mapping by the difference (delta)
    shift_script = text("""
        UPDATE lms_tt_time_table_day_mapping 
        SET class_date = DATE_ADD(STR_TO_DATE(class_date, '%Y-%m-%d'), INTERVAL :days DAY)
        WHERE tt_detail_id = :tt_id
    """)
    db.execute(shift_script, {"days": delta, "tt_id": req.tt_detail_id})
    
    # 3. Update the main detail table
    db.execute(text("UPDATE lms_tt_time_table_details SET tt_start_date = :d WHERE tt_detail_id = :id"), 
               {"d": req.new_start_date, "id": req.tt_detail_id})
    
    db.commit()
    return {"message": "Timetable dates reset/shifted successfully"}

# 4. API for Add/Delete classes based on date reduced or increased
@app.put("/api/v1/timetable/update-range")
def update_timetable_range(req: UpdateRangeRequest, db: Session = Depends(get_db)):
    """If end_date is reduced, delete classes. If increased, add classes based on weekly template."""
    res = db.execute(text("SELECT tt_end_date FROM lms_tt_time_table_details WHERE tt_detail_id = :id"), {"id": req.tt_detail_id}).fetchone()
    old_end = datetime.strptime(res[0], '%Y-%m-%d').date()

    if req.new_end_date < old_end:
        # REDUCED: Delete classes outside new range
        db.execute(text("DELETE FROM lms_tt_time_table_day_mapping WHERE tt_detail_id = :id AND class_date > :new_end"), 
                   {"id": req.tt_detail_id, "new_end": req.new_end_date})
    
    elif req.new_end_date > old_end:
        # INCREASED: Add classes from template for new days
        current_date = old_end + timedelta(days=1)
        while current_date <= req.new_end_date:
            # MySQL dayofweek: 1=Sun, 2=Mon... your day_id: 1=Mon, 7=Sun
            # We convert Python weekday (0=Mon) to your day_id (1=Mon)
            target_day_id = current_date.weekday() + 1 
            
            fill_script = text("""
                INSERT INTO lms_tt_time_table_day_mapping 
                (time_table_id, tt_detail_id, day_id, week_day_name, class_date, allot_crs_id, created_by)
                SELECT time_table_id, tt_detail_id, day_id, week_day_name, :c_date, crs_id, :user
                FROM lms_tt_time_table 
                WHERE tt_detail_id = :tt_id AND day_id = :d_id
            """)
            db.execute(fill_script, {"c_date": current_date, "user": req.user_id, "tt_id": req.tt_detail_id, "d_id": target_day_id})
            current_date += timedelta(days=1)

    # Update main table end date
    db.execute(text("UPDATE lms_tt_time_table_details SET tt_end_date = :d WHERE tt_detail_id = :id"), 
               {"d": req.new_end_date, "id": req.tt_detail_id})
    db.commit()
    return {"message": "Timetable range updated"}