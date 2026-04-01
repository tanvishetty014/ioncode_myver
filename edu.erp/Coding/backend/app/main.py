from fastapi import FastAPI, Request, Depends, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import date, datetime, timedelta
import time

# Internal imports
from .api.v1.routes import router as api_router
from .db.models import Base  
from .core.database import engine, SessionLocal 
from sqlalchemy.orm import Session
from sqlalchemy import text  
from pydantic import BaseModel

# --- SCHEMAS ---
class DropdownResponse(BaseModel):
    id: int
    name: str
from .db.models import Base
from .core.database import engine
#from app.api.v1.cudo_module.bloom_level import bloom_level as bloom_level_routes

class QuizListSchema(BaseModel):
    quiz_id: int
    title: str
    scheduled_date: datetime

class StudentMarkSchema(BaseModel):
    student_name: str
    roll_no: str
    secured_marks: Optional[float]
    status: str

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

# --- APP INITIALIZATION ---
app = FastAPI(title="IonCudos LMS API")

# --- CORS MIDDLEWARE (FIXED: This solves the CORS Policy Error) ---
origins = [
    "http://localhost:3000", # React Frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE DEPENDENCY ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- LOGGING MIDDLEWARE ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    print(f"REQUEST: {request.method} {request.url.path} - STATUS: {response.status_code} - TIME: {process_time:.2f}ms")
    return response

<<<<<<< HEAD
# Configuration for CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
    allow_origins=origins,
    # allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

app.include_router(api_router)

# cudo_module route include commented out because module is missing
#app.include_router(
#    bloom_level_routes.router,
#    prefix="/api/v1/cudo_module", 
#    tags=["Bloom Level"]
#)

# Include the main API router
=======
# --- ROUTER REGISTRATION (FIXED: This solves the 404 Not Found) ---
# Note: Since your routers (like comman_function) already define "/api/v1",
# we include them without a prefix here to prevent doubling up to "/api/v1/api/v1"
# main.py
# This adds the "/api/v1" part of the URL
>>>>>>> 03403f79f48c202752b10687ff8d046867d9239d
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to IonCudos API", "status": "Online"}

# =================================================================
# HIERARCHY & QUIZ APIs (Keep as is)
# =================================================================
@app.get("/api/v1/hierarchy/programs", response_model=List[DropdownResponse])
def get_programs(dept_id: int, db: Session = Depends(get_db)):
    # Real query to fetch programs based on the department selected
    query = text("SELECT pg_id AS id, pg_name AS name FROM iems_program WHERE dept_id = :dept_id")
    rows = db.execute(query, {"dept_id": dept_id}).mappings().all()
    return rows

# Add this to your main.py
@app.get("/api/v1/hierarchy/departments", response_model=List[DropdownResponse])
def get_departments(db: Session = Depends(get_db)):
    # This SQL query fetches real departments from your database
    query = text("SELECT dept_id AS id, dept_name AS name FROM iems_department ORDER BY dept_name ASC")
    rows = db.execute(query).mappings().all()
    
    # If the table is empty, it returns this dummy data so your UI doesn't break
    if not rows:
        return [{"id": 1, "name": "Computer Science"}, {"id": 2, "name": "Information Technology"}]
        
    return rows

@app.get("/api/v1/hierarchy/terms", response_model=List[DropdownResponse])
def get_terms(curriculum_id: int, db: Session = Depends(get_db)):
    # Real query to fetch terms (semesters) based on the curriculum (academic batch)
    query = text("""
        SELECT semester_id AS id, semester AS name 
        FROM iems_semester 
        WHERE academic_batch_id = :curriculum_id 
        ORDER BY semester_id ASC
    """)
    rows = db.execute(query, {"curriculum_id": curriculum_id}).mappings().all()
    
    # Fallback if no data is found so the dropdown doesn't look broken
    if not rows:
        return [{"id": 0, "name": "No Terms Found"}]
        
    return rows



# @app.get("/api/v1/hierarchy/terms", response_model=List[DropdownResponse])
# def get_terms(curriculum_id: int, db: Session = Depends(get_db)):
#     return [{"id": 4, "name": "Semester 4"}]

@app.get("/api/v1/hierarchy/sections", response_model=List[DropdownResponse])
def get_sections(term_id: int, db: Session = Depends(get_db)):
    # Real query to fetch sections based on the term (semester) selected
    query = text("""
        SELECT id AS id, section AS name 
        FROM iems_section 
        WHERE semester_id = :term_id 
        ORDER BY section ASC
    """)
    rows = db.execute(query, {"term_id": term_id}).mappings().all()
    
    if not rows:
        return [{"id": 0, "name": "No Sections Found"}]
        
    return rows

# =================================================================
# FIXED TIMETABLE LOGIC APIS (YOUR ASSIGNED TASKS)
# =================================================================

# 1. API for Copy Class Day
@app.post("/api/v1/timetable/copy-day")
def copy_class_day(req: CopyDayRequest, db: Session = Depends(get_db)):
    """Copies all classes from source_date to target_date."""
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

# 2. API for Delete Timetable Day
@app.delete("/api/v1/timetable/delete-day")
def delete_timetable_day(tt_detail_id: int, class_date: str, db: Session = Depends(get_db)):
    """Deletes class mappings for a single day."""
    delete_script = text("""
        DELETE FROM lms_tt_time_table_day_mapping 
        WHERE tt_detail_id = :tt_id AND class_date = :c_date
    """)
    result = db.execute(delete_script, {"tt_id": tt_detail_id, "c_date": class_date})
    db.commit()
    return {"message": f"Timetable for {class_date} deleted", "deleted_count": result.rowcount}

# 3. API for Reset Timetable Date (Shifting)
from sqlalchemy import text

import traceback # Put this at the very top of the file

@app.put("/api/v1/timetable/reset-date")
def reset_timetable_date(req: ResetTimetableRequest, db: Session = Depends(get_db)):
    print(f"DEBUG: Resetting Timetable ID {req.tt_detail_id} to {req.new_start_date}") # Check your terminal for this!
    
    try:
        # 1. Check if the timetable exists
        res = db.execute(
            text("SELECT tt_start_date FROM lms_tt_time_table_details WHERE tt_detail_id = :id"), 
            {"id": req.tt_detail_id}
        ).fetchone()
        
        if not res: 
            print("DEBUG: Timetable not found in DB")
            return {"status": False, "message": "Timetable not found"}
        
        # 2. Convert dates
        old_start_str = str(res[0])
        try:
            # Try standard format first
            old_start = datetime.strptime(old_start_str, '%Y-%m-%d').date()
        except:
            # If DB is DD-MM-YYYY
            old_start = datetime.strptime(old_start_str, '%d-%m-%Y').date()

        new_start = datetime.strptime(req.new_start_date, '%Y-%m-%d').date()
        delta = (new_start - old_start).days

        # 3. UPDATE THE MAPPING
        # We try both formats to be safe
        db.execute(text("""
            UPDATE lms_tt_time_table_day_mapping 
            SET class_date = DATE_FORMAT(DATE_ADD(STR_TO_DATE(class_date, '%d-%m-%Y'), INTERVAL :days DAY), '%d-%m-%Y')
            WHERE tt_detail_id = :tt_id
        """), {"days": delta, "tt_id": req.tt_detail_id})

        db.execute(text("""
            UPDATE lms_tt_time_table_day_mapping 
            SET class_date = DATE_ADD(class_date, INTERVAL :days DAY)
            WHERE tt_detail_id = :tt_id AND class_date NOT LIKE '%-%-%'
        """), {"days": delta, "tt_id": req.tt_detail_id})

        # 4. UPDATE THE MAIN DETAILS TABLE
        db.execute(
            text("UPDATE lms_tt_time_table_details SET tt_start_date = :d WHERE tt_detail_id = :id"), 
            {"d": req.new_start_date, "id": req.tt_detail_id}
        )

        db.commit()
        print("DEBUG: Reset Successful")
        return {"status": True, "message": "Timetable shifted successfully", "delta": delta}

    except Exception as e:
        db.rollback()
        print("!!! ERROR DETECTED !!!")
        print(traceback.format_exc()) # THIS WILL SHOW THE REAL ERROR IN TERMINAL
        return {"status": False, "message": str(e)} # This will show the real error in React

# 4. API for Update Range (Add/Delete based on range change)
@app.put("/api/v1/timetable/update-range")
def update_timetable_range(req: UpdateRangeRequest, db: Session = Depends(get_db)):
    """If end_date is reduced, delete classes. If increased, add from template."""
    res = db.execute(text("SELECT tt_end_date FROM lms_tt_time_table_details WHERE tt_detail_id = :id"), {"id": req.tt_detail_id}).fetchone()
    if not res:
        raise HTTPException(status_code=404, detail="Timetable record not found")

    old_end = datetime.strptime(str(res[0]), '%Y-%m-%d').date()
    new_end = datetime.strptime(req.new_end_date, '%Y-%m-%d').date()

    if new_end < old_end:
        # REDUCED: Delete classes outside new range
        db.execute(text("DELETE FROM lms_tt_time_table_day_mapping WHERE tt_detail_id = :id AND class_date > :new_end"), 
                   {"id": req.tt_detail_id, "new_end": req.new_end_date})
    
    elif new_end > old_end:
        # INCREASED: Fill from weekly template
        current_date = old_end + timedelta(days=1)
        while current_date <= new_end:
            target_day_id = current_date.weekday() + 1 
            fill_script = text("""
                INSERT INTO lms_tt_time_table_day_mapping 
                (time_table_id, tt_detail_id, day_id, week_day_name, class_date, allot_crs_id, created_by)
                SELECT time_table_id, tt_detail_id, day_id, week_day_name, :c_date, crs_id, :user
                FROM lms_tt_time_table 
                WHERE tt_detail_id = :tt_id AND day_id = :d_id
            """)
            db.execute(fill_script, {"c_date": current_date.strftime('%Y-%m-%d'), "user": req.user_id, "tt_id": req.tt_detail_id, "id": target_day_id})
            current_date += timedelta(days=1)

    db.execute(text("UPDATE lms_tt_time_table_details SET tt_end_date = :d WHERE tt_detail_id = :id"), 
               {"d": req.new_end_date, "id": req.tt_detail_id})
    db.commit()
    return {"message": "Timetable range updated successfully"}