import mysql.connector
from fastapi import APIRouter, Path, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from ...core.database import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USERNAME

router = APIRouter()


def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=int(DB_PORT),
    )


def _database_error_response(exc: mysql.connector.Error):
    return JSONResponse(
        status_code=500,
        content=jsonable_encoder(
            {
                "status": 500,
                "message": f"Database error: {exc}",
                "data": None,
            }
        ),
    )


@router.get("/student")
def get_student_notifications(student_usn: str = Query(..., min_length=1)):
    query = """
        SELECT
            msn.lmsn_id,
            msn.lmsn_det_id,
            msn.student_usn,
            COALESCE(NULLIF(TRIM(s.name), ''), msn.student_usn) AS student_name,
            n.notify_description,
            n.notify_attachment,
            n.notify_document_url,
            n.delivery_date,
            n.delivery_time,
            n.delivery_hide_date,
            n.delivery_hide_time,
            COALESCE(msn.notify_seen_flag, 0) AS is_read,
            msn.notify_seenon_datetime
        FROM lms_map_student_notifications msn
        INNER JOIN lms_notifications n
            ON n.lmsn_id = msn.lmsn_id
        INNER JOIN lms_notifications_details nd
            ON nd.lmsn_det_id = msn.lmsn_det_id
        LEFT JOIN (
            SELECT
                TRIM(LOWER(usno)) AS normalized_usno,
                MAX(NULLIF(TRIM(name), '')) AS name
            FROM iems_students
            WHERE usno IS NOT NULL AND TRIM(usno) <> ''
            GROUP BY TRIM(LOWER(usno))
        ) s
            ON s.normalized_usno = TRIM(LOWER(msn.student_usn))
        WHERE TRIM(LOWER(msn.student_usn)) = TRIM(LOWER(%s))
          AND nd.student_flag = 1
          AND TIMESTAMP(n.delivery_date, COALESCE(n.delivery_time, '00:00:00')) <= NOW()
          AND (
                n.delivery_hide_date IS NULL
                OR TIMESTAMP(
                    n.delivery_hide_date,
                    COALESCE(n.delivery_hide_time, '23:59:59')
                ) > NOW()
              )
        ORDER BY n.delivery_date DESC, COALESCE(n.delivery_time, '00:00:00') DESC, msn.lmsn_id DESC
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (student_usn,))
        rows = cursor.fetchall()

        data = [
            {
                "lmsn_id": row["lmsn_id"],
                "lmsn_det_id": row["lmsn_det_id"],
                "student_usn": row["student_usn"],
                "student_name": row["student_name"],
                "notify_description": row["notify_description"],
                "notify_attachment": row["notify_attachment"],
                "notify_document_url": row["notify_document_url"],
                "delivery_date": row["delivery_date"],
                "delivery_time": row["delivery_time"],
                "delivery_hide_date": row["delivery_hide_date"],
                "delivery_hide_time": row["delivery_hide_time"],
                "is_read": int(row["is_read"] or 0),
                "notify_seenon_datetime": row["notify_seenon_datetime"],
            }
            for row in rows
        ]

        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(
                {
                    "status": 200,
                    "message": "Student notifications fetched successfully",
                    "data": data,
                }
            ),
        )
    except mysql.connector.Error as exc:
        return _database_error_response(exc)
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


@router.get("/student/unread-count")
def get_student_unread_notifications_count(student_usn: str = Query(..., min_length=1)):
    query = """
        SELECT COUNT(*) AS unread_count
        FROM lms_map_student_notifications msn
        INNER JOIN lms_notifications n
            ON n.lmsn_id = msn.lmsn_id
        INNER JOIN lms_notifications_details nd
            ON nd.lmsn_det_id = msn.lmsn_det_id
        WHERE TRIM(LOWER(msn.student_usn)) = TRIM(LOWER(%s))
          AND nd.student_flag = 1
          AND TIMESTAMP(n.delivery_date, COALESCE(n.delivery_time, '00:00:00')) <= NOW()
          AND (
                n.delivery_hide_date IS NULL
                OR TIMESTAMP(
                    n.delivery_hide_date,
                    COALESCE(n.delivery_hide_time, '23:59:59')
                ) > NOW()
              )
          AND COALESCE(msn.notify_seen_flag, 0) = 0
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (student_usn,))
        row = cursor.fetchone() or {"unread_count": 0}

        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(
                {
                    "status": 200,
                    "message": "Unread count fetched successfully",
                    "data": {
                        "unread_count": int(row["unread_count"] or 0),
                    },
                }
            ),
        )
    except mysql.connector.Error as exc:
        return _database_error_response(exc)
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


@router.put("/{lmsn_id}/read")
def mark_student_notification_as_read(
    lmsn_id: int = Path(...),
    student_usn: str = Query(..., min_length=1),
    lmsn_det_id: int = Query(...),
):
    query = """
        UPDATE lms_map_student_notifications
        SET notify_seen_flag = 1,
            notify_seenon_datetime = NOW()
        WHERE TRIM(LOWER(student_usn)) = TRIM(LOWER(%s))
          AND lmsn_id = %s
          AND lmsn_det_id = %s
    """

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, (student_usn, lmsn_id, lmsn_det_id))
        connection.commit()

        if cursor.rowcount == 0:
            return JSONResponse(
                status_code=404,
                content=jsonable_encoder(
                    {
                        "status": 404,
                        "message": "Notification mapping not found",
                        "data": None,
                    }
                ),
            )

        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(
                {
                    "status": 200,
                    "message": "Notification marked as read successfully",
                    "data": {
                        "lmsn_id": lmsn_id,
                        "lmsn_det_id": lmsn_det_id,
                        "student_usn": student_usn,
                    },
                }
            ),
        )
    except mysql.connector.Error as exc:
        if connection is not None:
            connection.rollback()
        return _database_error_response(exc)
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()
