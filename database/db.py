"""SQLite database access for MSU Registration Helper."""

import csv
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import config
from models.course import Course, CourseAction, CourseStatus


class DatabaseManager:
    """Owns the local queue, saved course profiles, and registration history."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.DB_PATH
        self._create_tables()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _create_tables(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_code TEXT NOT NULL,
                    section TEXT NOT NULL,
                    name TEXT DEFAULT '',
                    credit TEXT DEFAULT '',
                    seat TEXT DEFAULT '',
                    time TEXT DEFAULT '',
                    curriculum_structure TEXT DEFAULT '',
                    status TEXT DEFAULT 'queued',
                    message TEXT DEFAULT '',
                    action TEXT DEFAULT 'add',
                    saved_course_id INTEGER,
                    profile_id INTEGER,
                    created_at TEXT NOT NULL
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER,
                    saved_course_id INTEGER,
                    course_code TEXT NOT NULL,
                    section TEXT NOT NULL,
                    name TEXT DEFAULT '',
                    result TEXT NOT NULL,
                    message TEXT DEFAULT '',
                    action TEXT DEFAULT 'add',
                    registered_at TEXT NOT NULL
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS course_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    academic_term TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS saved_courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER NOT NULL,
                    course_code TEXT NOT NULL,
                    section TEXT NOT NULL,
                    note TEXT DEFAULT '',
                    priority INTEGER DEFAULT 0,
                    enabled INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(profile_id) REFERENCES course_profiles(id) ON DELETE CASCADE
                )
                """
            )

            self._ensure_column(cursor, "courses", "action", "TEXT DEFAULT 'add'")
            self._ensure_column(cursor, "courses", "saved_course_id", "INTEGER")
            self._ensure_column(cursor, "courses", "profile_id", "INTEGER")
            self._ensure_column(cursor, "courses", "credit", "TEXT DEFAULT ''")
            self._ensure_column(cursor, "courses", "seat", "TEXT DEFAULT ''")
            self._ensure_column(cursor, "courses", "time", "TEXT DEFAULT ''")
            self._ensure_column(cursor, "courses", "curriculum_structure", "TEXT DEFAULT ''")
            self._ensure_column(cursor, "history", "action", "TEXT DEFAULT 'add'")
            self._ensure_column(cursor, "history", "profile_id", "INTEGER")
            self._ensure_column(cursor, "history", "saved_course_id", "INTEGER")

    def _ensure_column(self, cursor: sqlite3.Cursor, table: str, column: str, definition: str):
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except sqlite3.OperationalError:
            pass

    # Current registration queue

    def add_course(self, course: Course, profile_id: Optional[int] = None, saved_course_id: Optional[int] = None) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO courses
                    (course_code, section, name, credit, seat, time, curriculum_structure, status, message, action, saved_course_id, profile_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    course.course_code,
                    course.section,
                    course.name,
                    course.credit,
                    course.seat,
                    course.time,
                    course.curriculum_structure,
                    course.status.value,
                    course.message,
                    course.action.value,
                    saved_course_id,
                    profile_id,
                    course.created_at.isoformat(),
                ),
            )
            return cursor.lastrowid

    def replace_courses_from_web(self, rows: list[dict]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM courses")
            for row in rows:
                cursor.execute(
                    """
                    INSERT INTO courses
                        (course_code, section, name, credit, seat, time, curriculum_structure, status, message, action, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("course_code", ""),
                        row.get("section", ""),
                        row.get("course_name", row.get("name", "")),
                        row.get("credit", ""),
                        row.get("seat", ""),
                        row.get("time", ""),
                        row.get("curriculum_structure", ""),
                        row.get("status_value", CourseStatus.PENDING.value),
                        row.get("status", ""),
                        row.get("action", CourseAction.ADD.value),
                        datetime.now().isoformat(),
                    ),
                )

    def get_courses(self) -> list[Course]:
        with self._get_connection() as conn:
            rows = conn.cursor().execute("SELECT * FROM courses ORDER BY id").fetchall()

        courses = []
        for row in rows:
            try:
                status = CourseStatus(row["status"])
            except ValueError:
                status = CourseStatus.UNKNOWN
            try:
                action = CourseAction(row["action"])
            except (ValueError, KeyError, TypeError):
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
                    credit=row["credit"] or "",
                    seat=row["seat"] or "",
                    time=row["time"] or "",
                    curriculum_structure=row["curriculum_structure"] or "",
                    status=status,
                    message=row["message"] or "",
                    action=action,
                    created_at=created_at,
                )
            )
        return courses

    def get_course_row(self, course_id: int) -> Optional[dict]:
        with self._get_connection() as conn:
            row = conn.cursor().execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        return dict(row) if row else None

    def update_course_status(self, course_id: int, status: str, message: str = ""):
        with self._get_connection() as conn:
            conn.cursor().execute(
                "UPDATE courses SET status = ?, message = ? WHERE id = ?",
                (status, message, course_id),
            )

    def update_course_name(self, course_id: int, name: str):
        with self._get_connection() as conn:
            conn.cursor().execute("UPDATE courses SET name = ? WHERE id = ?", (name, course_id))

    def remove_course(self, course_id: int):
        with self._get_connection() as conn:
            conn.cursor().execute("DELETE FROM courses WHERE id = ?", (course_id,))

    def clear_courses(self):
        with self._get_connection() as conn:
            conn.cursor().execute("DELETE FROM courses")

    # Saved course profiles

    def create_profile(self, name: str, academic_term: str) -> int:
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO course_profiles (name, academic_term, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (name.strip(), academic_term.strip(), now, now),
            )
            return cursor.lastrowid

    def get_profiles(self) -> list[dict]:
        with self._get_connection() as conn:
            rows = conn.cursor().execute(
                "SELECT * FROM course_profiles ORDER BY updated_at DESC, id DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def update_profile(self, profile_id: int, name: str, academic_term: str):
        with self._get_connection() as conn:
            conn.cursor().execute(
                """
                UPDATE course_profiles
                SET name = ?, academic_term = ?, updated_at = ?
                WHERE id = ?
                """,
                (name.strip(), academic_term.strip(), datetime.now().isoformat(), profile_id),
            )

    def delete_profile(self, profile_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM saved_courses WHERE profile_id = ?", (profile_id,))
            cursor.execute("DELETE FROM course_profiles WHERE id = ?", (profile_id,))

    def add_saved_course(
        self,
        profile_id: int,
        course_code: str,
        section: str,
        note: str = "",
        priority: Optional[int] = None,
        enabled: bool = True,
    ) -> int:
        if priority is None:
            existing = self.get_saved_courses_by_profile(profile_id)
            priority = max([c["priority"] for c in existing], default=0) + 1
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO saved_courses
                    (profile_id, course_code, section, note, priority, enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    course_code.strip(),
                    section.strip(),
                    note.strip(),
                    int(priority),
                    1 if enabled else 0,
                    datetime.now().isoformat(),
                ),
            )
            cursor.execute(
                "UPDATE course_profiles SET updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), profile_id),
            )
            return cursor.lastrowid

    def update_saved_course(
        self,
        course_id: int,
        course_code: str,
        section: str,
        note: str = "",
        priority: int = 0,
        enabled: bool = True,
    ):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE saved_courses
                SET course_code = ?, section = ?, note = ?, priority = ?, enabled = ?
                WHERE id = ?
                """,
                (course_code.strip(), section.strip(), note.strip(), int(priority), 1 if enabled else 0, course_id),
            )
            row = cursor.execute("SELECT profile_id FROM saved_courses WHERE id = ?", (course_id,)).fetchone()
            if row:
                cursor.execute(
                    "UPDATE course_profiles SET updated_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), row["profile_id"]),
                )

    def delete_saved_course(self, course_id: int):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            row = cursor.execute("SELECT profile_id FROM saved_courses WHERE id = ?", (course_id,)).fetchone()
            cursor.execute("DELETE FROM saved_courses WHERE id = ?", (course_id,))
            if row:
                cursor.execute(
                    "UPDATE course_profiles SET updated_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), row["profile_id"]),
                )

    def get_saved_courses_by_profile(self, profile_id: int) -> list[dict]:
        with self._get_connection() as conn:
            rows = conn.cursor().execute(
                """
                SELECT * FROM saved_courses
                WHERE profile_id = ?
                ORDER BY priority ASC, id ASC
                """,
                (profile_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    # History and exports

    def add_history(self, course: Course):
        self.save_registration_result(
            course_code=course.course_code,
            section=course.section,
            name=course.name,
            result=course.status.value,
            message=course.message,
            action=course.action.value,
        )

    def save_registration_result(
        self,
        course_code: str,
        section: str,
        result: str,
        message: str = "",
        name: str = "",
        action: str = "add",
        profile_id: Optional[int] = None,
        saved_course_id: Optional[int] = None,
    ):
        with self._get_connection() as conn:
            conn.cursor().execute(
                """
                INSERT INTO history
                    (profile_id, saved_course_id, course_code, section, name, result, message, action, registered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    saved_course_id,
                    course_code,
                    section,
                    name,
                    result,
                    message,
                    action,
                    datetime.now().isoformat(),
                ),
            )

    def get_history(self, limit: int = 50) -> list[dict]:
        with self._get_connection() as conn:
            rows = conn.cursor().execute(
                "SELECT * FROM history ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()

        return [
            {
                "id": row["id"],
                "profile_id": row["profile_id"],
                "saved_course_id": row["saved_course_id"],
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
        self.export_registration_history_csv(filepath)

    def export_registration_history_csv(self, filepath: str):
        history = self.get_history(limit=999999)
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "id",
                    "profile_id",
                    "saved_course_id",
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

    def export_profile_csv(self, profile_id: int, filepath: str):
        profile = next((p for p in self.get_profiles() if p["id"] == profile_id), None)
        courses = self.get_saved_courses_by_profile(profile_id)
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "profile_name",
                    "academic_term",
                    "course_code",
                    "section",
                    "note",
                    "priority",
                    "enabled",
                ],
            )
            writer.writeheader()
            for c in courses:
                writer.writerow(
                    {
                        "profile_name": profile["name"] if profile else "",
                        "academic_term": profile["academic_term"] if profile else "",
                        "course_code": c["course_code"],
                        "section": c["section"],
                        "note": c["note"],
                        "priority": c["priority"],
                        "enabled": c["enabled"],
                    }
                )

    def import_profile_csv(self, filepath: str, fallback_name: str = "Imported Profile") -> int:
        with open(filepath, "r", newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            raise ValueError("CSV file has no saved courses.")

        first = rows[0]
        profile_id = self.create_profile(
            first.get("profile_name") or fallback_name,
            first.get("academic_term") or "",
        )
        for idx, row in enumerate(rows, start=1):
            if not row.get("course_code") or not row.get("section"):
                continue
            enabled_text = str(row.get("enabled", "1")).strip().lower()
            self.add_saved_course(
                profile_id=profile_id,
                course_code=row.get("course_code", ""),
                section=row.get("section", ""),
                note=row.get("note", ""),
                priority=int(row.get("priority") or idx),
                enabled=enabled_text not in {"0", "false", "no", "disabled"},
            )
        return profile_id
