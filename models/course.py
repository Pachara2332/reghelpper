"""Course data model."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class CourseStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FULL = "full"
    CONFLICT = "conflict"
    INVALID = "invalid"
    FAILED = "failed"
    SKIPPED = "skipped"
    NOT_FOUND = "not_found"
    UNKNOWN = "unknown"
    QUEUED = "queued"

    @property
    def display_text(self) -> str:
        mapping = {
            "pending": "รอบันทึก / Pending",
            "success": "สำเร็จ / Success",
            "full": "เต็ม / Full",
            "conflict": "ชนตาราง / Conflict",
            "invalid": "ไม่ถูกต้อง / Invalid",
            "failed": "ล้มเหลว / Failed",
            "skipped": "ข้าม / Skipped",
            "not_found": "ไม่พบ / Not found",
            "unknown": "ไม่ทราบ / Unknown",
            "queued": "รอคิว / Queued",
        }
        return mapping.get(self.value, self.value)

    @property
    def emoji(self) -> str:
        mapping = {
            "pending": "...",
            "success": "OK",
            "full": "FULL",
            "conflict": "!",
            "invalid": "!",
            "failed": "x",
            "skipped": "-",
            "not_found": "?",
            "unknown": "?",
            "queued": "Q",
        }
        return mapping.get(self.value, "?")


class CourseAction(Enum):
    ADD = "add"
    DROP = "drop"

    @property
    def display_text(self) -> str:
        mapping = {
            "add": "เพิ่ม / Add",
            "drop": "ถอน / Drop",
        }
        return mapping.get(self.value, self.value)


@dataclass
class Course:
    course_code: str
    section: str
    name: str = ""
    credit: str = ""
    seat: str = ""
    time: str = ""
    curriculum_structure: str = ""
    status: CourseStatus = CourseStatus.QUEUED
    message: str = ""
    action: CourseAction = CourseAction.ADD
    created_at: datetime = field(default_factory=datetime.now)
    id: Optional[int] = None
