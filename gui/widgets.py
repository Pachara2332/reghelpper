"""Custom Qt widgets for the MSU Registration Helper UI."""

from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QSize, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QWidget,
)

from gui.lang import Lang, get_lang, t
from models.course import Course, CourseStatus


def _status_text(status: CourseStatus) -> str:
    mapping_th = {
        CourseStatus.QUEUED: "รอคิว",
        CourseStatus.PENDING: "รอยืนยัน",
        CourseStatus.SUCCESS: "สำเร็จ",
        CourseStatus.FULL: "เต็ม",
        CourseStatus.CONFLICT: "ชนตาราง",
        CourseStatus.INVALID: "ไม่ถูกต้อง",
        CourseStatus.FAILED: "ล้มเหลว",
        CourseStatus.SKIPPED: "ข้าม",
        CourseStatus.NOT_FOUND: "ไม่พบ",
        CourseStatus.UNKNOWN: "ไม่ทราบ",
    }
    mapping_en = {
        CourseStatus.QUEUED: "Queued",
        CourseStatus.PENDING: "Pending",
        CourseStatus.SUCCESS: "Success",
        CourseStatus.FULL: "Full",
        CourseStatus.CONFLICT: "Conflict",
        CourseStatus.INVALID: "Invalid",
        CourseStatus.FAILED: "Failed",
        CourseStatus.SKIPPED: "Skipped",
        CourseStatus.NOT_FOUND: "Not found",
        CourseStatus.UNKNOWN: "Unknown",
    }
    mapping = mapping_th if get_lang() == Lang.TH else mapping_en
    return mapping.get(status, status.value)


class RegistrationQueueTableWidget(QTableWidget):
    """Table for displaying actual registration queue from confirm_enroll.asp."""

    course_removed = pyqtSignal(int)

    HEADERS_TH = [
        "รหัสวิชา",
        "ชื่อรายวิชา",
        "หน่วยกิต",
        "กลุ่ม",
        "สถานะ",
        "จัดการ",
    ]
    HEADERS_EN = [
        "Code",
        "Course name",
        "Credit",
        "Section",
        "Status",
        "Action",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(6)
        self._apply_headers()

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)

    def _apply_headers(self):
        labels = self.HEADERS_TH if get_lang() == Lang.TH else self.HEADERS_EN
        self.setHorizontalHeaderLabels(labels)

    def refresh_lang(self):
        self._apply_headers()

    def set_courses(self, courses: list[Course]):
        self.setRowCount(0)
        for course in courses:
            self.add_course_row(course)

    def add_course_row(self, course: Course):
        row_idx = self.rowCount()
        self.insertRow(row_idx)

        values = [
            course.course_code,
            course.name,
            getattr(course, "credit", ""),
            course.section,
            _status_text(course.status),
        ]

        row_data = {
            "course_code": course.course_code,
            "section": course.section,
            "db_id": course.id,
        }

        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value or ""))
            if col in {0, 2, 3, 4}:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setData(Qt.ItemDataRole.UserRole, row_data)
            self.setItem(row_idx, col, item)

        # Action: Delete button
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        btn = QPushButton("X")
        btn.setObjectName("dangerButton")
        btn.setFixedSize(QSize(28, 28))
        btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        db_id = course.id
        btn.setEnabled(db_id is not None)
        btn.clicked.connect(lambda checked, cid=db_id: self._on_delete_clicked(cid))
        layout.addWidget(btn)
        self.setCellWidget(row_idx, 5, container)

    def _on_delete_clicked(self, course_id: int):
        if course_id is not None:
            self.course_removed.emit(int(course_id))

    def update_row_status(self, course_id: int, status: CourseStatus, name: str = "", message: str = ""):
        for r in range(self.rowCount()):
            row_data = self.item(r, 0).data(Qt.ItemDataRole.UserRole) if self.item(r, 0) else {}
            if row_data.get("db_id") == course_id:
                if name:
                    self.item(r, 1).setText(name)
                self.item(r, 4).setText(_status_text(status))
                break

    def clear_all(self):
        self.setRowCount(0)


class LogPanel(QTextEdit):
    """Simple color-coded log panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaxLength(500)

    def setMaxLength(self, limit: int):
        self.limit = limit

    def log(self, message: str, level: str = "info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "info": "#c9d1d9",
            "success": "#3fb950",
            "error": "#f85149",
            "warning": "#d29922",
            "system": "#58a6ff",
        }
        color = colors.get(level, "#c9d1d9")
        log_html = f'<span style="color: #8b949e;">{timestamp} &gt;</span> <span style="color: {color};">{message}</span>'
        self.append(log_html)
        self.moveCursor(self.textCursor().MoveOperation.End)

    def clear_log(self):
        self.clear()


class StatusIndicator(QWidget):
    """Browser status light."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.status = "disconnected"
        self.text = t("ยังไม่ได้เปิดเบราว์เซอร์", "Browser not open")
        self.colors = {
            "connected": QColor("#3fb950"),
            "disconnected": QColor("#8b949e"),
            "waiting": QColor("#d29922"),
            "error": QColor("#f85149"),
        }

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.light = QLabel()
        self.light.setFixedSize(14, 14)
        layout.addWidget(self.light)

        self.label = QLabel(self.text)
        self.label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.label)

        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._toggle_pulse)
        self.pulse_visible = True
        self._update_style()

    def set_status(self, status: str, text: str):
        self.status = status
        self.text = text
        self.label.setText(text)
        if status == "waiting":
            if not self.pulse_timer.isActive():
                self.pulse_timer.start(500)
        else:
            self.pulse_timer.stop()
            self.pulse_visible = True
        self._update_style()

    def _toggle_pulse(self):
        self.pulse_visible = not self.pulse_visible
        self._update_style()

    def _update_style(self):
        color = self.colors.get(self.status, QColor("#8b949e"))
        if self.status == "waiting" and not self.pulse_visible:
            color = QColor("transparent")

        from PyQt6.QtGui import QPixmap

        pixmap = QPixmap(14, 14)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(0, 0, 14, 14)
        painter.end()
        self.light.setPixmap(pixmap)
