"""
MSU Registration Helper — Database Manager
จัดการฐานข้อมูล SQLite สำหรับเก็บรายวิชาและประวัติการลงทะเบียน
"""

import csv
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import config
from models.course import Course, CourseStatus


class DatabaseManager:
    """
    จัดการฐานข้อมูล SQLite สำหรับระบบลงทะเบียน

    - ตาราง courses: เก็บรายวิชาที่ต้องการลงทะเบียน (คิวปัจจุบัน)
    - ตาราง history: เก็บประวัติผลการลงทะเบียนทั้งหมด
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        สร้าง DatabaseManager และสร้างตารางถ้ายังไม่มี

        Args:
            db_path: พาธไฟล์ฐานข้อมูล ถ้าไม่ระบุจะใช้ค่าจาก config.DB_PATH
        """
        self.db_path = db_path or config.DB_PATH
        self._create_tables()

    @contextmanager
    def _get_connection(self):
        """
        Context manager สำหรับเปิด/ปิด connection อัตโนมัติ
        ใช้ check_same_thread=False เพื่อรองรับการเรียกจากหลาย thread
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _create_tables(self):
        """สร้างตาราง courses และ history ถ้ายังไม่มี"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # ตาราง courses — เก็บรายวิชาในคิวปัจจุบัน
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_code TEXT NOT NULL,
                    section TEXT NOT NULL,
                    name TEXT DEFAULT '',
                    status TEXT DEFAULT 'queued',
                    message TEXT DEFAULT '',
                    action TEXT DEFAULT 'add',
                    created_at TEXT NOT NULL
                )
            """)

            # ตาราง history — เก็บประวัติผลการลงทะเบียน
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_code TEXT NOT NULL,
                    section TEXT NOT NULL,
                    name TEXT DEFAULT '',
                    result TEXT NOT NULL,
                    message TEXT DEFAULT '',
                    action TEXT DEFAULT 'add',
                    registered_at TEXT NOT NULL
                )
            """)
            
            # อัปเกรดฐานข้อมูลเพื่อเพิ่มคอลัมน์ action (กรณีมีไฟล์ db เดิมอยู่แล้ว)
            try:
                cursor.execute("ALTER TABLE courses ADD COLUMN action TEXT DEFAULT 'add'")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE history ADD COLUMN action TEXT DEFAULT 'add'")
            except sqlite3.OperationalError:
                pass

    # ─── Course CRUD ─────────────────────────────────────────────

    def add_course(self, course: Course) -> int:
        """
        เพิ่มรายวิชาเข้าคิว

        Args:
            course: ออบเจกต์ Course ที่ต้องการเพิ่ม

        Returns:
            id ของรายวิชาที่เพิ่ม
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO courses (course_code, section, name, status, message, action, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    course.course_code,
                    course.section,
                    course.name,
                    course.status.value,
                    course.message,
                    course.action.value,
                    course.created_at.isoformat(),
                ),
            )
            return cursor.lastrowid

    def get_courses(self) -> list[Course]:
        """
        ดึงรายวิชาทั้งหมดในคิวปัจจุบัน

        Returns:
            รายการ Course ทั้งหมด เรียงตาม id
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM courses ORDER BY id")
            rows = cursor.fetchall()

        courses = []
        for row in rows:
            try:
                status = CourseStatus(row["status"])
            except ValueError:
                status = CourseStatus.UNKNOWN

            try:
                from models.course import CourseAction
                action = CourseAction(row["action"])
            except (ValueError, KeyError, TypeError):
                from models.course import CourseAction
                action = CourseAction.ADD

            try:
                created_at = datetime.fromisoformat(row["created_at"])
            except (ValueError, TypeError):
                created_at = datetime.now()

            courses.append(
                Course(
                    id=row["id"],
                    course_code=row["course_code"],
                    section=row["section"],
                    name=row["name"] or "",
                    status=status,
                    message=row["message"] or "",
                    action=action,
                    created_at=created_at,
                )
            )
        return courses

    def update_course_status(self, course_id: int, status: str, message: str = ""):
        """
        อัปเดตสถานะของรายวิชา

        Args:
            course_id: ID ของรายวิชา
            status: สถานะใหม่ (เช่น 'success', 'full')
            message: ข้อความเพิ่มเติมจากระบบ
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE courses SET status = ?, message = ? WHERE id = ?",
                (status, message, course_id),
            )

    def remove_course(self, course_id: int):
        """
        ลบรายวิชาออกจากคิว

        Args:
            course_id: ID ของรายวิชาที่ต้องการลบ
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))

    def clear_courses(self):
        """ลบรายวิชาทั้งหมดออกจากคิว"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM courses")

    # ─── History ─────────────────────────────────────────────────

    def add_history(self, course: Course):
        """
        บันทึกผลการลงทะเบียนลงประวัติ

        Args:
            course: ออบเจกต์ Course ที่ต้องการบันทึกประวัติ
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO history (course_code, section, name, result, message, action, registered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    course.course_code,
                    course.section,
                    course.name,
                    course.status.value,
                    course.message,
                    course.action.value,
                    datetime.now().isoformat(),
                ),
            )

    def get_history(self, limit: int = 50) -> list[dict]:
        """
        ดึงประวัติการลงทะเบียนล่าสุด

        Args:
            limit: จำนวนรายการสูงสุดที่ต้องการดึง (ค่าเริ่มต้น 50)

        Returns:
            รายการ dict ของประวัติ เรียงจากล่าสุดก่อน
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM history ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "course_code": row["course_code"],
                "section": row["section"],
                "name": row["name"] or "",
                "result": row["result"],
                "message": row["message"] or "",
                "action": row["action"] or "add",
                "registered_at": row["registered_at"],
            }
            for row in rows
        ]

    def export_csv(self, filepath: str):
        """
        ส่งออกประวัติการลงทะเบียนเป็นไฟล์ CSV

        Args:
            filepath: พาธไฟล์ CSV ที่ต้องการบันทึก
        """
        history = self.get_history(limit=999999)

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "id",
                    "course_code",
                    "section",
                    "name",
                    "result",
                    "message",
                    "action",
                    "registered_at",
                ],
            )
            writer.writeheader()
            writer.writerows(history)
