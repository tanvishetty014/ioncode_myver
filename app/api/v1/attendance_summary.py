from datetime import datetime

import mysql.connector
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from ...core.database import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USERNAME

router = APIRouter(prefix="/attendance-summary", tags=["Attendance Summary"])


def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=int(DB_PORT),
    )


@router.get("")
def get_attendance_summary(
    from_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    to_date: str = Query(..., description="End date in YYYY-MM-DD format"),
):
    try:
        parsed_from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
        parsed_to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={
                "status": 400,
                "message": "from_date and to_date must be in YYYY-MM-DD format",
                "data": [],
            },
        )

    if parsed_from_date > parsed_to_date:
        return JSONResponse(
            status_code=400,
            content={
                "status": 400,
                "message": "from_date cannot be greater than to_date",
                "data": [],
            },
        )

    query = """
        SELECT
            MIN(s.student_id) AS student_id,
            s.usno,
            COUNT(
                CASE
                    WHEN LOWER(TRIM(a.attendance_status)) IN ('present', 'p', '1') THEN 1
                END
            ) AS present,
            COUNT(
                CASE
                    WHEN LOWER(TRIM(a.attendance_status)) IN ('absent', 'a', '0') THEN 1
                END
            ) AS absent
        FROM iems_students s
        LEFT JOIN lms_map_student_attendance a
            ON TRIM(LOWER(a.student_usn)) = TRIM(LOWER(s.usno))
        LEFT JOIN lms_manage_attendance ma
            ON ma.attendance_id = a.attendance_id
            AND DATE(ma.created_at) BETWEEN %s AND %s
        GROUP BY s.usno
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (from_date, to_date))
        rows = cursor.fetchall()

        data = [
            {
                "student_id": int(row["student_id"]) if row["student_id"] is not None else None,
                "usno": row["usno"],
                "present": int(row["present"] or 0),
                "absent": int(row["absent"] or 0),
            }
            for row in rows
        ]

        return JSONResponse(
            status_code=200,
            content={
                "status": 200,
                "message": "Attendance fetched successfully",
                "data": data,
            },
        )
    except mysql.connector.Error as exc:
        return JSONResponse(
            status_code=500,
            content={
                "status": 500,
                "message": f"Database error: {exc}",
                "data": [],
            },
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
