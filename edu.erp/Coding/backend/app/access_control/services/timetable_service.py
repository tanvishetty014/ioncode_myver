from sqlalchemy.orm import Session
from datetime import date, timedelta, datetime
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
            semester=cls.semester,
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
                        semester=t_cls.semester,
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