from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from datetime import date, timedelta, datetime
from typing import Optional
from typing import List, Dict
from app.db import models  # This points to your models.py file
from fastapi import HTTPException, status

def delete_timetable_logic(db: Session, sem_time_table_id: int):
    """Requirement: Delete Timetable and its associated custom entries"""
    # 1. Delete associated scheduled entries in the custom timetable first (Foreign Key cleanup)
    # NOTE: Ensure the column name is correct (is it .id or .sem_time_table_id?)
    db.query(models.IEMSCustomTimeTable).filter(
        models.IEMSCustomTimeTable.sem_time_table_id == sem_time_table_id 
    ).delete(synchronize_session=False)
    
    # 2. Delete the main header
    timetable = db.query(models.IEMSemTimeTable).filter(models.IEMSemTimeTable.id == sem_time_table_id).first()
    if not timetable:
        return False
        
    db.delete(timetable)
    db.commit()
    return True

def reset_timetable_dates_logic(db: Session, sem_time_table_id: int):
    """Requirement: Reset Timetable Date (Clears the calendar for this timetable)"""
    # Check if timetable exists first
    exists = db.query(models.IEMSemTimeTable).filter(models.IEMSemTimeTable.id == sem_time_table_id).first()
    if not exists:
        return False

    db.query(models.IEMSCustomTimeTable).filter(
        models.IEMSCustomTimeTable.sem_time_table_id == sem_time_table_id
    ).delete(synchronize_session=False)
    
    db.commit()
    return True

def copy_class_day_logic(db: Session, source_date: date, target_date: date, section: str):
    """Requirement: Copy Class Day (Fixes '0 classes copied' error)"""
    
    # 1. VALIDATION: Find the classes to copy
    source_classes = db.query(models.IEMSCustomTimeTable).filter(
        models.IEMSCustomTimeTable.date == source_date,
        models.IEMSCustomTimeTable.section == section
    ).all()

    # If no classes found, return 0. The Router will then throw a 404 based on this.
    if not source_classes:
        return 0

    # 2. Check if target date already has classes (to avoid duplicates)
    existing_target_classes = db.query(models.IEMSCustomTimeTable).filter(
        models.IEMSCustomTimeTable.date == target_date,
        models.IEMSCustomTimeTable.section == section
    ).first()
    
    if existing_target_classes:
        # Optional: You can choose to delete existing or raise an error
        # For now, we return 0 to indicate no NEW classes were copied via this logic
        return 0

    new_entries = []
    for cls in source_classes:
        # Create a new instance without the original primary key (ID)
        new_class = models.IEMSCustomTimeTable(
            pgm_id=cls.pgm_id,
            dept_id=cls.dept_id,
            academic_batch=cls.academic_batch,
            semester_id=cls.semester,
            section=cls.section,
            date=target_date, # Use the NEW date
            start_time=cls.start_time,
            end_time=cls.end_time,
            crs_code=cls.crs_code,
            tt_batch_id=cls.tt_batch_id,
            faculty_id=cls.faculty_id,
            status=cls.status,
            org_id=cls.org_id,
            created_by=cls.created_by,
            created_on=datetime.now(),
            modified_by=cls.modified_by,
            modified_on=datetime.now(),
            batch_name=cls.batch_name,
            sem_time_table_id=cls.sem_time_table_id # Ensure FK is preserved
        )
        new_entries.append(new_class)
    
    db.add_all(new_entries)
    db.commit()
    return len(new_entries)

def sync_timetable_dates_logic(db: Session, sem_time_table_id: int, new_end_date: date):
    """Requirement: Add/Delete classes based on date range extension or reduction"""
    
    # 1. Get the current latest scheduled date for this timetable
    latest_class = db.query(models.IEMSCustomTimeTable).filter(
        models.IEMSCustomTimeTable.sem_time_table_id == sem_time_table_id
    ).order_by(models.IEMSCustomTimeTable.date.desc()).first()

    if not latest_class:
        return 0

    old_end_date = latest_class.date

    # CASE A: Date Reduced (DELETE classes beyond the new end date)
    if new_end_date < old_end_date:
        deleted_count = db.query(models.IEMSCustomTimeTable).filter(
            models.IEMSCustomTimeTable.sem_time_table_id == sem_time_table_id,
            models.IEMSCustomTimeTable.date > new_end_date
        ).delete(synchronize_session=False)
        db.commit()
        return deleted_count

    # CASE B: Date Increased (ADD classes using the last available day as a template)
    elif new_end_date > old_end_date:
        # Use the classes from the old_end_date as a pattern for new days
        template_classes = db.query(models.IEMSCustomTimeTable).filter(
            models.IEMSCustomTimeTable.sem_time_table_id == sem_time_table_id,
            models.IEMSCustomTimeTable.date == old_end_date
        ).all()

        if not template_classes:
            return 0

        new_entries = []
        current_date = old_end_date + timedelta(days=1)

        while current_date <= new_end_date:
            # Only add classes for Weekdays (0=Mon, 4=Fri)
            if current_date.weekday() <= 4: 
                for t_cls in template_classes:
                    new_class = models.IEMSCustomTimeTable(
                        pgm_id=t_cls.pgm_id,
                        dept_id=t_cls.dept_id,
                        academic_batch=t_cls.academic_batch,
                        semester_id=t_cls.semester,
                        section=t_cls.section,
                        date=current_date,
                        start_time=t_cls.start_time,
                        end_time=t_cls.end_time,
                        crs_code=t_cls.crs_code,
                        faculty_id=t_cls.faculty_id,
                        status=t_cls.status,
                        org_id=t_cls.org_id,
                        created_on=datetime.now(),
                        batch_name=t_cls.batch_name,
                        sem_time_table_id=sem_time_table_id
                    )
                    new_entries.append(new_class)
            current_date += timedelta(days=1)
        
        db.add_all(new_entries)
        db.commit()
        return len(new_entries)

    return 0


def get_timetable_created_dates_for_course(db: Session, crs_code: str):
    """Return distinct creation dates (date part of `created_on`) for custom timetable entries of a course."""
    rows = db.query(models.IEMSCustomTimeTable.created_on).filter(
        models.IEMSCustomTimeTable.crs_code == crs_code
    ).all()

    # Extract date portion and unique
    dates = sorted({r[0].date() for r in rows if r[0] is not None})
    return dates


def is_lesson_scheduled_on_date(db: Session, crs_code: str, day: date, section: Optional[str] = None):
    """Return True/False whether any scheduled class exists for given course on a date; optionally filter by section."""
    query = db.query(models.IEMSCustomTimeTable).filter(
        models.IEMSCustomTimeTable.crs_code == crs_code,
        models.IEMSCustomTimeTable.date == day
    )
    if section:
        query = query.filter(models.IEMSCustomTimeTable.section == section)

    exists = db.query(query.exists()).scalar()
    return bool(exists)


def get_scheduled_class_timings(db: Session, crs_code: str, day: date, section: Optional[str] = None):
    """Return list of scheduled class timings for a course on a date (optionally filtered by section)."""
    query = db.query(
        models.IEMSCustomTimeTable.start_time,
        models.IEMSCustomTimeTable.end_time,
        models.IEMSCustomTimeTable.section,
        models.IEMSCustomTimeTable.faculty_id,
        models.IEMSCustomTimeTable.batch_name
    ).filter(
        models.IEMSCustomTimeTable.crs_code == crs_code,
        models.IEMSCustomTimeTable.date == day
    )
    if section:
        query = query.filter(models.IEMSCustomTimeTable.section == section)

    rows = query.order_by(models.IEMSCustomTimeTable.start_time).all()

    timings = [
        {
            "start_time": r[0],
            "end_time": r[1],
            "section": r[2],
            "faculty_id": r[3],
            "batch_name": r[4]
        }
        for r in rows
    ]
    return timings


def get_attendance_for_timing(db: Session, crs_code: str, day: date, start_time: str, end_time: str, section: Optional[str] = None, sem_time_table_id: Optional[int] = None) -> List[Dict]:
    """Fetch attendance rows for a specific class timing."""
    query = db.query(
        models.IEMSDailyAttendance.attendance_id,
        models.IEMSDailyAttendance.regno,
        models.IEMSDailyAttendance.usno,
        models.IEMSDailyAttendance.student_id,
        models.IEMSDailyAttendance.attendance_status,
        models.IEMSDailyAttendance.other_reason,
        models.IEMSDailyAttendance.posted_date,
        models.IEMSDailyAttendance.is_extra_class
    ).filter(
        models.IEMSDailyAttendance.crs_code == crs_code,
        models.IEMSDailyAttendance.result_year == day,
        models.IEMSDailyAttendance.start_time == start_time,
        models.IEMSDailyAttendance.end_time == end_time
    )

    if section:
        query = query.filter(models.IEMSDailyAttendance.section == section)
    if sem_time_table_id:
        query = query.filter(models.IEMSDailyAttendance.sem_time_table_id == sem_time_table_id)

    rows = query.all()
    return [
        {
            "attendance_id": r[0],
            "regno": r[1],
            "usno": r[2],
            "student_id": r[3],
            "attendance_status": r[4],
            "other_reason": r[5],
            "posted_date": r[6],
            "is_extra_class": r[7]
        }
        for r in rows
    ]


def save_attendance_batch(db: Session, attendance_list: List[Dict], meta: Dict) -> Dict:
    """Save or update attendance entries.

    attendance_list: list of dicts with keys: regno, usno(optional), student_id(optional), attendance_status, other_reason(optional), is_extra_class(optional)
    meta: dict with class context: crs_code, result_year (date), start_time, end_time, section, sem_time_table_id, user_id
    Returns counts of created/updated rows.
    """
    created = 0
    updated = 0
    now = datetime.utcnow()

    crs_code = meta.get("crs_code")
    result_year = meta.get("result_year")
    start_time = meta.get("start_time")
    end_time = meta.get("end_time")
    section = meta.get("section")
    sem_time_table_id = meta.get("sem_time_table_id")
    user_id = meta.get("user_id")

    for item in attendance_list:
        regno = item.get("regno")
        student_id = item.get("student_id")
        usno = item.get("usno")
        status_val = item.get("attendance_status")
        other = item.get("other_reason")
        is_extra = item.get("is_extra_class", 0)

        if not regno:
            continue

        # Find existing record
        existing = db.query(models.IEMSDailyAttendance).filter(
            models.IEMSDailyAttendance.crs_code == crs_code,
            models.IEMSDailyAttendance.result_year == result_year,
            models.IEMSDailyAttendance.start_time == start_time,
            models.IEMSDailyAttendance.end_time == end_time,
            models.IEMSDailyAttendance.regno == regno
        )
        if section:
            existing = existing.filter(models.IEMSDailyAttendance.section == section)
        if sem_time_table_id:
            existing = existing.filter(models.IEMSDailyAttendance.sem_time_table_id == sem_time_table_id)

        existing_row = existing.first()
        if existing_row:
            # Update
            existing_row.attendance_status = status_val
            existing_row.other_reason = other
            existing_row.user_id = user_id
            existing_row.posted_date = now
            existing_row.updated_date = now
            existing_row.is_extra_class = is_extra
            db.add(existing_row)
            updated += 1
        else:
            # Insert
            new_row = models.IEMSDailyAttendance(
                result_year=result_year,
                crs_code=crs_code,
                student_id=student_id,
                regno=regno,
                usno=usno,
                section=section,
                start_time=start_time,
                end_time=end_time,
                attendance_status=status_val,
                other_reason=other,
                user_id=user_id,
                sem_time_table_id=sem_time_table_id,
                posted_date=now,
                created_date=now,
                updated_date=now,
                is_extra_class=is_extra
            )
            db.add(new_row)
            created += 1

    db.commit()
    return {"created": created, "updated": updated}


def get_attendance_lesson_dates(
    db: Session,
    academic_batch_id: int,
    semester_id: int,
    course_id: int,
    section_id: int,
) -> List[date]:
    """Fetch distinct scheduled lesson dates for attendance calendar highlighting."""
    query = text(
        """
        SELECT DISTINCT ls.plan_date AS lesson_date
        FROM lms_lesson_schedule ls
        WHERE ls.academic_batch_id = :academic_batch_id
            AND ls.semester_id = :semester_id
            AND ls.section_id = :section_id
            AND ls.plan_date IS NOT NULL
        ORDER BY ls.plan_date
        """
    )

    try:
        rows = db.execute(
            query,
            {
                "academic_batch_id": academic_batch_id,
                "semester_id": semester_id,
                "course_id": course_id,
                "section_id": section_id,
            },
        ).fetchall()
        return [row[0] for row in rows if row[0] is not None]
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch lesson dates: {exc}",
        ) from exc


def get_attendance_summary(
    db: Session,
    academic_batch_id: Optional[int],
    semester_id: Optional[int],
    course_id: Optional[int],
    section_id: Optional[int],
    from_date: Optional[date],
    to_date: Optional[date],
    only_present: bool = False,
) -> List[Dict]:
    """Return student-wise present/absent attendance summary."""
    print(
        "Attendance summary params:",
        {
            "academic_batch_id": academic_batch_id,
            "semester_id": semester_id,
            "course_id": course_id,
            "section_id": section_id,
            "from_date": from_date,
            "to_date": to_date,
            "only_present": only_present,
        },
    )

    conditions = []
    params: Dict = {}

    if academic_batch_id is not None:
        conditions.append("ma.academic_batch_id = :academic_batch_id")
        params["academic_batch_id"] = academic_batch_id
    if semester_id is not None:
        conditions.append("ma.semester_id = :semester_id")
        params["semester_id"] = semester_id
    if course_id is not None:
        conditions.append("ma.crs_id = :crs_id")
        params["crs_id"] = course_id
    if section_id is not None:
        conditions.append("ma.section_id = :section_id")
        params["section_id"] = section_id
    if from_date is not None and to_date is not None:
        conditions.append("ma.attendance_date BETWEEN :from_date AND :to_date")
        params["from_date"] = from_date
        params["to_date"] = to_date
    elif from_date is not None:
        conditions.append("ma.attendance_date >= :from_date")
        params["from_date"] = from_date
    elif to_date is not None:
        conditions.append("ma.attendance_date <= :to_date")
        params["to_date"] = to_date

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    having_clause = "HAVING COUNT(CASE WHEN msa.attendance_status = 'Present' THEN 1 END) > 0" if only_present else ""

    query = text(
        f"""
        SELECT 
            COALESCE(
                NULLIF(TRIM(s.name), ''),
                NULLIF(TRIM(CONCAT_WS(' ', s.first_name, s.middle_name, s.last_name)), ''),
                s.usno
            ) AS name,
            COUNT(CASE WHEN msa.attendance_status = 'Present' THEN 1 END) AS present,
            COUNT(CASE WHEN msa.attendance_status = 'Absent' THEN 1 END) AS absent
        FROM lms_manage_attendance ma
        JOIN lms_map_student_attendance msa 
            ON ma.attendance_id = msa.attendance_id
        JOIN iems_students s 
            ON s.usno = msa.student_usn
        {where_clause}
        GROUP BY s.name, s.first_name, s.middle_name, s.last_name, s.usno
        {having_clause}
        ORDER BY name
        """
    )

    try:
        rows = db.execute(query, params).fetchall()
        print("Attendance summary raw rows:", rows)

        students = [
            {
                "name": row.name,
                "present": int(row.present or 0),
                "absent": int(row.absent or 0),
            }
            for row in rows
        ]
        print("Attendance summary mapped students:", students)
        return students
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch attendance summary: {exc}",
        ) from exc
