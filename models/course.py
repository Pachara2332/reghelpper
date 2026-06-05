"""
MSU Registration Helper — Course Model
โมเดลข้อมูลรายวิชาและสถานะการลงทะเบียน
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional


class CourseStatus(Enum):
    """สถานะของรายวิชาที่ต้องการลงทะเบียน"""

    PENDING = 'pending'
    SUCCESS = 'success'
    FULL = 'full'
    CONFLICT = 'conflict'
    NOT_FOUND = 'not_found'
    UNKNOWN = 'unknown'
    QUEUED = 'queued'  # อยู่ในคิวรอลง

    @property
    def display_text(self) -> str:
        """แปลงสถานะเป็นข้อความภาษาไทยสำหรับแสดงผล"""
        mapping = {
            'pending': 'รอยืนยัน',
            'success': 'ลงทะเบียนสำเร็จ',
            'full': 'ที่นั่งเต็ม',
            'conflict': 'เวลาเรียนชนกัน',
            'not_found': 'ไม่พบรายวิชา',
            'unknown': 'ไม่ทราบผลลัพธ์',
            'queued': 'อยู่ในคิว',
        }
        return mapping.get(self.value, self.value)

    @property
    def emoji(self) -> str:
        """ส่งคืน emoji ที่แสดงสถานะ"""
        mapping = {
            'pending': '⏳',
            'success': '✅',
            'full': '🔴',
            'conflict': '🟡',
            'not_found': '⚫',
            'unknown': '❓',
            'queued': '📋',
        }
        return mapping.get(self.value, '❓')


class CourseAction(Enum):
    """ประเภทการทำรายการ (ลงทะเบียน / ลดรายวิชา)"""
    ADD = 'add'
    DROP = 'drop'

    @property
    def display_text(self) -> str:
        mapping = {
            'add': '➕ ลงทะเบียน',
            'drop': '➖ ลดรายวิชา'
        }
        return mapping.get(self.value, self.value)


@dataclass
class Course:
    """
    ข้อมูลรายวิชาที่ต้องการลงทะเบียน

    Attributes:
        course_code: รหัสวิชา เช่น '0001001'
        section: หมู่เรียน เช่น '1'
        name: ชื่อวิชา (ได้จากระบบหลังจากเพิ่มวิชา)
        status: สถานะปัจจุบัน
        message: ข้อความเพิ่มเติมจากระบบ
        action: ประเภทการทำรายการ (ลงทะเบียน หรือ ลดรายวิชา)
        created_at: เวลาที่เพิ่มวิชานี้เข้าคิว
        id: ID ในฐานข้อมูล (None ถ้ายังไม่ได้บันทึก)
    """

    course_code: str
    section: str
    name: str = ''
    status: CourseStatus = CourseStatus.QUEUED
    message: str = ''
    action: CourseAction = CourseAction.ADD
    created_at: datetime = field(default_factory=datetime.now)
    id: Optional[int] = None

