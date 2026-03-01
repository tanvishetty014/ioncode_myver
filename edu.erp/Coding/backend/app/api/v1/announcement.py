from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone

from ...core.database import get_db
from ...utils.http_return_helper import returnSuccess, returnException
from ...db.models import Announcement, StudentNotificationMap

router = APIRouter(prefix="/announcements", tags=["Announcements"])


@router.get("/received/{user_id}")
def get_received_announcements(user_id: int, db: Session = Depends(get_db)):

    notifications = (
        db.query(
            Announcement.lmsn_id,
            Announcement.notify_description,
            Announcement.delivery_date,
            Announcement.delivery_time,
            Announcement.created_at,
            StudentNotificationMap.notify_seen_flag,
            StudentNotificationMap.notify_seenon_datetime,
        )
        .join(
            StudentNotificationMap,
            StudentNotificationMap.lmsn_id == Announcement.lmsn_id,
        )
        .filter(StudentNotificationMap.ssd_id == user_id)
        .order_by(Announcement.created_at.desc())
        .all()
    )

    data = [
        {
            "id": n.lmsn_id,
            "description": n.notify_description,
            "delivery_date": n.delivery_date,
            "delivery_time": n.delivery_time,
            "created_at": n.created_at,
            "seen_flag": n.notify_seen_flag,
            "seen_on": n.notify_seenon_datetime,
        }
        for n in notifications
    ]

    return returnSuccess(data)

@router.get("/unseen-count/{user_id}")
def get_unseen_count(user_id: int, db: Session = Depends(get_db)):

    count = (
        db.query(func.count(StudentNotificationMap.lms_msn_id))
        .join(
            Announcement,
            Announcement.lmsn_id == StudentNotificationMap.lmsn_id,
        )
        .filter(
            StudentNotificationMap.ssd_id == user_id,
            StudentNotificationMap.notify_seen_flag == 0,
        )
        .scalar()
    )

    return returnSuccess({"unseen_count": count or 0})

@router.post("/mark-seen/{announcement_id}/{user_id}")
def mark_announcement_seen(
    announcement_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):

    existing = db.query(StudentNotificationMap).filter(
        StudentNotificationMap.lmsn_id == announcement_id,
        StudentNotificationMap.ssd_id == user_id
    ).first()

    if existing:
        existing.notify_seen_flag = 1
        existing.notify_seenon_datetime = datetime.now(timezone.utc)
    else:
        return returnException("Notification mapping not found")

    db.commit()

    return returnSuccess(None, "Marked as seen")
