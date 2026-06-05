"""
MSU Registration Helper — Custom Widgets
รวบรวมวิดเจ็ตปรับแต่งเฉพาะทางสำหรับแอปพลิเคชัน GUI
"""

from datetime import datetime
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QTextEdit, QWidget, 
    QHBoxLayout, QLabel, QPushButton, QHeaderView
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush

from models.course import Course, CourseStatus

class CourseTableWidget(QTableWidget):
    """
    ตารางแสดงรายการวิชาในคิวลงทะเบียน
    มีฟังก์ชันเพิ่มวิชา, ลบ, อัปเดตสถานะ, และดึงข้อมูลรายวิชา
    """
    # Signal ส่งออกเมื่อมีการกดลบวิชา (ส่งค่า course_id)
    course_removed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels(["#", "รหัสวิชา", "หมู่เรียน", "ประเภททำรายการ", "ชื่อวิชา", "สถานะ", "จัดการ"])
        
        # ปรับการจัดขนาดคอลัมน์
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    def add_course_row(self, course: Course):
        """เพิ่มแถวข้อมูลรายวิชาใหม่ลงตาราง"""
        row_idx = self.rowCount()
        self.insertRow(row_idx)

        # 0. ลำดับหรือ ID
        id_item = QTableWidgetItem(str(course.id if course.id else row_idx + 1))
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        id_item.setData(Qt.ItemDataRole.UserRole, course.id) # เก็บ ID ซ่อนไว้
        self.setItem(row_idx, 0, id_item)

        # 1. รหัสวิชา
        code_item = QTableWidgetItem(course.course_code)
        code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row_idx, 1, code_item)

        # 2. หมู่เรียน
        sec_item = QTableWidgetItem(course.section)
        sec_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row_idx, 2, sec_item)

        # 3. ประเภททำรายการ (Badge: Add / Drop)
        from models.course import CourseAction
        act_badge = QLabel(course.action.display_text)
        act_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if course.action == CourseAction.ADD:
            act_badge.setStyleSheet("color: #58a6ff; font-weight: bold; padding: 2px 4px;")
        else:
            act_badge.setStyleSheet("color: #ff7b72; font-weight: bold; padding: 2px 4px;")
        
        container_act = QWidget()
        layout_act = QHBoxLayout(container_act)
        layout_act.addWidget(act_badge)
        layout_act.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_act.setContentsMargins(0, 0, 0, 0)
        self.setCellWidget(row_idx, 3, container_act)

        # 4. ชื่อวิชา
        name_item = QTableWidgetItem(course.name or "กำลังโหลด...")
        self.setItem(row_idx, 4, name_item)

        # 5. สถานะ (ใช้ Custom Label เป็น Badge)
        self._set_status_badge(row_idx, course.status)

        # 6. ปุ่มลบ
        del_btn = QPushButton("✕")
        del_btn.setObjectName("dangerButton")
        del_btn.setFixedSize(QSize(28, 28))
        del_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        # เชื่อมปุ่มลบ
        course_db_id = course.id
        del_btn.clicked.connect(lambda: self._on_delete_clicked(course_db_id, row_idx))
        
        # จัดปุ่มให้อยู่กึ่งกลางใน cell
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addWidget(del_btn)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setCellWidget(row_idx, 6, container)

    def _set_status_badge(self, row: int, status: CourseStatus):
        """ตั้งค่าสถานะเป็น Badge สีต่างๆ"""
        badge = QLabel(status.display_text)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # กำหนด ID เพื่อให้ตรงตาม Stylesheet QSS
        if status == CourseStatus.QUEUED:
            badge.setObjectName("statusBadgeNotFound") # สีเทา
        elif status == CourseStatus.PENDING:
            badge.setObjectName("statusBadgePending") # สีน้ำเงิน
        elif status == CourseStatus.SUCCESS:
            badge.setObjectName("statusBadgeSuccess") # สีเขียว
        elif status == CourseStatus.FULL:
            badge.setObjectName("statusBadgeFull") # สีแดง
        elif status == CourseStatus.CONFLICT:
            badge.setObjectName("statusBadgeConflict") # สีส้ม
        else:
            badge.setObjectName("statusBadgeNotFound")

        # จัดให้อยู่กึ่งกลางใน cell
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addWidget(badge)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(4, 4, 4, 4)
        self.setCellWidget(row, 5, container)

    def update_row_status(self, course_id: int, status: CourseStatus, name: str = "", message: str = ""):
        """อัปเดตสถานะวิชาตาม course_id ที่พบในตาราง"""
        for r in range(self.rowCount()):
            item = self.item(r, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == course_id:
                # อัปเดตสถานะ badge
                self._set_status_badge(r, status)
                # อัปเดตชื่อวิชาถ้าส่งมา
                if name:
                    self.item(r, 4).setText(name)
                break

    def _on_delete_clicked(self, course_id: Optional[int], row_idx: int):
        """เมื่อคลิกปุ่มลบ"""
        # ส่งสัญญาณออกไปเพื่อลบจาก Database
        if course_id is not None:
            self.course_removed.emit(course_id)
        
        # ลบออกจาก TableWidget
        # เนื่องจากปุ่มกดได้หลายครั้ง ต้องค้นหาแถวใหม่เผื่อ row index มีการขยับ
        if course_id is not None:
            for r in range(self.rowCount()):
                item = self.item(r, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) == course_id:
                    self.removeRow(r)
                    break
        else:
            self.removeRow(row_idx)

    def get_all_courses(self) -> list:
        """ดึงรายการข้อมูลรายวิชาในตารางออกมาทั้งหมด"""
        courses = []
        for r in range(self.rowCount()):
            id_item = self.item(r, 0)
            code_item = self.item(r, 1)
            sec_item = self.item(r, 2)
            name_item = self.item(r, 4)
            
            if id_item and code_item and sec_item:
                courses.append({
                    "id": id_item.data(Qt.ItemDataRole.UserRole),
                    "course_code": code_item.text(),
                    "section": sec_item.text(),
                    "name": name_item.text() if name_item else ""
                })
        return courses

    def clear_all(self):
        """ล้างตารางทั้งหมด"""
        self.setRowCount(0)



class LogPanel(QTextEdit):
    """
    หน้าต่างแสดงประวัติการทำงานของระบบ (System Logs)
    จัดแต่งสีตาม Level ของความผิดพลาด
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaxLength(500) # เก็บประวัติไม่เกิน 500 บรรทัด

    def setMaxLength(self, limit: int):
        self.limit = limit

    def log(self, message: str, level: str = "info"):
        """
        เขียน log ลงแผงควบคุม
        Levels: 'info', 'success', 'error', 'warning', 'system'
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # กำหนดสี HTML ตามประเภท Log
        colors = {
            "info": "#c9d1d9",       # เทาขาว
            "success": "#3fb950",    # เขียว
            "error": "#f85149",      # แดง
            "warning": "#d29922",    # เหลือง
            "system": "#58a6ff"      # น้ำเงิน
        }
        color = colors.get(level, "#c9d1d9")
        
        log_html = f'<span style="color: #8b949e;">{timestamp} ▸</span> <span style="color: {color};">{message}</span>'
        self.append(log_html)
        
        # เลื่อนลงไปล่างสุดอัตโนมัติ
        self.moveCursor(self.textCursor().MoveOperation.End)

    def clear_log(self):
        """ล้างประวัติ log ทั้งหมด"""
        self.clear()


class StatusIndicator(QWidget):
    """
    ดวงไฟแสดงสถานะ (Status indicator circle) 
    มาพร้อมเอฟเฟกต์กระพริบเมื่อรอคิว
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.status = "disconnected"
        self.text = "ยังไม่ได้เชื่อมต่อเบราว์เซอร์"
        
        # ตัวบ่งชี้สี
        self.colors = {
            "connected": QColor("#3fb950"),      # เขียว
            "disconnected": QColor("#8b949e"),   # เทา
            "waiting": QColor("#d29922"),        # ส้มเหลือง
            "error": QColor("#f85149")           # แดง
        }
        
        # จัดการเลเอาต์
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # ดวงไฟกลม
        self.light = QLabel()
        self.light.setFixedSize(14, 14)
        layout.addWidget(self.light)
        
        # ข้อความคำอธิบาย
        self.label = QLabel(self.text)
        self.label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.label)
        
        # ตั้งค่าเอฟเฟกต์กระพริบ (Pulsing) เมื่อสถานะเฝ้าคิว
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self._toggle_pulse)
        self.pulse_visible = True
        
        self._update_style()

    def set_status(self, status: str, text: str):
        """ตั้งค่าสถานะ"""
        self.status = status
        self.text = text
        self.label.setText(text)
        
        if status == "waiting":
            if not self.pulse_timer.isActive():
                self.pulse_timer.start(500) # กระพริบทุกๆ 0.5 วินาที
        else:
            self.pulse_timer.stop()
            self.pulse_visible = True
            
        self._update_style()

    def _toggle_pulse(self):
        """สำหรับทำเอฟเฟกต์กระพริบ"""
        self.pulse_visible = not self.pulse_visible
        self._update_style()

    def _update_style(self):
        """วาดและอัปเดตสีของดวงไฟตามสถานะ"""
        color = self.colors.get(self.status, QColor("#8b949e"))
        
        # ถ้าอยู่ในสถานะซ่อนคีย์การกระพริบ
        if self.status == "waiting" and not self.pulse_visible:
            color = QColor("transparent")
            
        # สร้างพิกเซลแมปเพื่อวาดวงกลม
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
