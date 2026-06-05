"""Main PyQt6 application window."""

import os
import queue
import time
from datetime import datetime
from typing import Optional, Any

from PyQt6.QtCore import QLocale, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QGroupBox,
)

import config
from automation.browser import BrowserController
from automation.register import RegistrationService, classify_result_message
from database.db import DatabaseManager
from gui.styles import DARK_THEME_QSS
from gui.widgets import RegistrationQueueTableWidget, LogPanel, StatusIndicator
from gui.lang import Lang, get_lang, set_lang, t
from models.course import Course, CourseAction, CourseStatus


def ui_text(thai: str, english: str) -> str:
    return t(thai, english)


def normalize_status(status: str) -> str:
    if status == "not_found":
        return CourseStatus.INVALID.value
    if status == "unknown":
        return CourseStatus.FAILED.value
    return status


class BrowserWorker(QThread):
    status_update = pyqtSignal(str, str)
    login_status = pyqtSignal(bool)
    student_id_update = pyqtSignal(str)
    queue_synced = pyqtSignal(list)
    course_result = pyqtSignal(dict)
    register_all_finished = pyqtSignal()
    log_message = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.cmd_queue = queue.Queue()
        self.browser: Optional[BrowserController] = None
        self.register_service: Optional[RegistrationService] = None
        self.running = True
        self.synced_after_login = False

    def run(self):
        self.log_message.emit("ระบบเบราว์เซอร์พร้อม / Browser worker ready.", "system")
        self.browser = BrowserController()

        while self.running:
            try:
                cmd = self.cmd_queue.get(timeout=1.0)
                cmd_type = cmd.get("type")

                if cmd_type == "open_browser":
                    self._handle_open_browser()
                elif cmd_type == "check_login":
                    self._handle_check_login()
                elif cmd_type == "sync_queue":
                    self._handle_sync_queue()
                elif cmd_type == "add_course":
                    self._handle_add_course(cmd["course_code"], cmd["section"])
                elif cmd_type == "register_all":
                    self._handle_confirm_registration()
                elif cmd_type == "close_all":
                    self._handle_close()
                    break

                self.cmd_queue.task_done()
            except queue.Empty:
                if self.browser and self.browser.is_open:
                    if self.browser.detect_waiting_room():
                        self.status_update.emit("waiting", "waiting_room")
                        ready = self.browser.wait_for_page_ready(timeout_seconds=10)
                        if ready == "ready":
                            self.status_update.emit("connected", "logged_in" if self.browser.is_logged_in() else "opened_not_logged")
                    is_logged = self.browser.is_logged_in()
                    self.login_status.emit(is_logged)
                    self.student_id_update.emit(self.browser.get_student_id() if is_logged else "")
                    if is_logged and not self.synced_after_login and self.register_service:
                        self._handle_sync_queue()
                    if not is_logged:
                        self.synced_after_login = False
                    self.browser.keep_alive()
            except Exception as exc:
                self.log_message.emit(f"Worker error: {exc}", "error")
                self.error_occurred.emit(str(exc))

    def submit_command(self, cmd_type: str, **kwargs):
        cmd = {"type": cmd_type}
        cmd.update(kwargs)
        self.cmd_queue.put(cmd)

    def _handle_open_browser(self):
        self.log_message.emit("กำลังเปิดเบราว์เซอร์ / Opening browser...", "info")
        self.status_update.emit("waiting", "opening")
        try:
            page = self.browser.open_browser()
            self.register_service = RegistrationService(page)
            is_logged = self.browser.is_logged_in()
            self.login_status.emit(is_logged)
            self.student_id_update.emit(self.browser.get_student_id() if is_logged else "")
            self.status_update.emit("connected", "logged_in" if is_logged else "opened_not_logged")
            if is_logged:
                self._handle_sync_queue()
        except Exception as exc:
            self.status_update.emit("error", "error_open")
            self.log_message.emit(f"Cannot open browser: {exc}", "error")
            self.browser.take_screenshot("browser_open_error")

    def _handle_check_login(self):
        if not self.browser or not self.browser.is_open:
            self.log_message.emit("กรุณาเปิดเบราว์เซอร์ก่อน / Please open browser first.", "warning")
            return
        is_logged = self.browser.is_logged_in()
        self.login_status.emit(is_logged)
        self.student_id_update.emit(self.browser.get_student_id() if is_logged else "")
        if is_logged:
            self._handle_sync_queue()
            self.status_update.emit("connected", "logged_in")
            self.log_message.emit("ล็อกอินแล้ว พร้อมใช้งาน / Logged in and ready.", "success")
        else:
            self.status_update.emit("connected", "opened_not_logged")
            self.log_message.emit("ยังไม่ได้ล็อกอิน / Not logged in.", "warning")

    def _handle_sync_queue(self):
        if not self.browser or not self.browser.is_open or not self.register_service:
            return
        if not self.browser.is_logged_in():
            return
        try:
            self.status_update.emit("waiting", "syncing")
            rows = self.register_service.sync_existing_pending_courses()
            self.queue_synced.emit(rows)
            self.synced_after_login = True
            self.status_update.emit("connected", "synced")
            self.log_message.emit(f"ซิงก์คิวแล้วพบรายการค้าง / Synced queue: {len(rows)} items", "success")
        except Exception as exc:
            self.status_update.emit("connected", "logged_in")
            self.log_message.emit(f"Sync failed: {exc}", "error")

    def _handle_add_course(self, course_code: str, section: str):
        if not self.browser or not self.browser.is_open or not self.register_service:
            self.log_message.emit("ยังไม่ได้เปิดเบราว์เซอร์ / Browser not open.", "warning")
            return
        if not self.browser.is_logged_in():
            self.log_message.emit("กรุณาล็อกอินก่อน / Please log in first.", "warning")
            return
        try:
            self.status_update.emit("waiting", "adding_course")
            result = self.register_service.add_course_by_code_and_section(course_code, section)
            
            # Update queue rows from the live page
            self.queue_synced.emit(result["queue"])
            
            status = result["status"]
            message = result["message"]
            self.status_update.emit("connected", "add_done")
            
            status_labels = {
                "success": ("ลงทะเบียน/เพิ่มรายวิชาสำเร็จ", "Course added successfully"),
                "full": ("กลุ่มเรียนเต็ม", "Section full"),
                "conflict": ("เวลาเรียนชนกัน", "Time conflict"),
                "invalid": ("รหัสวิชาไม่ถูกต้อง", "Invalid course code"),
                "pending": ("เพิ่มลงคิวแล้ว (รอยืนยัน)", "Added to pending queue"),
                "unknown": ("ไม่สามารถตรวจสอบสถานะได้", "Unknown status"),
            }
            label_th, label_en = status_labels.get(status, ("ล้มเหลว", "Failed"))
            self.log_message.emit(f"{course_code} Sec {section} -> {t(label_th, label_en)}: {message}", "success" if status in {"success", "pending"} else "warning")
            
            if status not in {"success", "pending"}:
                self.error_occurred.emit(f"{course_code} Sec {section} -> {t(label_th, label_en)}\n{message}")
        except Exception as exc:
            self.status_update.emit("connected", "logged_in")
            self.log_message.emit(f"Add course failed: {exc}", "error")
            self.error_occurred.emit(str(exc))

    def _handle_confirm_registration(self):
        if not self.browser or not self.browser.is_open or not self.register_service:
            self.log_message.emit("ยังไม่ได้เปิดเบราว์เซอร์ / Browser not open.", "error")
            self.register_all_finished.emit()
            return
        if not self.browser.is_logged_in():
            self.log_message.emit("กรุณาล็อกอินก่อน / Please log in first.", "warning")
            self.register_all_finished.emit()
            return
        try:
            ok = self.register_service.confirm_registration()
            rows = self.register_service.refresh_registration_queue()
            self.queue_synced.emit(rows)
            self.log_message.emit(
                "ยืนยันเรียบร้อยแล้ว / Confirmed successfully on website." if ok else "ไม่พบปุ่มยืนยัน / Confirm button not found.",
                "success" if ok else "warning",
            )
        except Exception as exc:
            self.log_message.emit(f"Confirmation failed: {exc}", "error")
        self.register_all_finished.emit()

    def _handle_close(self):
        if self.browser:
            self.log_message.emit("กำลังปิดเบราว์เซอร์ / Closing browser...", "system")
            self.browser.close()
            self.status_update.emit("disconnected", "disconnected")


class HistoryDialog(QDialog):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.setStyleSheet(DARK_THEME_QSS)
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(ui_text("ประวัติการลงทะเบียน", "Registration History"))
        self.resize(760, 500)
        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            ui_text("เวลา", "Time"),
            ui_text("รหัสวิชา", "Code"),
            ui_text("หมู่", "Section"),
            ui_text("ชื่อวิชา", "Name"),
            ui_text("ผลลัพธ์", "Result"),
            ui_text("ข้อความ", "Message"),
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        export_btn = QPushButton(ui_text("ส่งออก CSV", "Export CSV"))
        close_btn = QPushButton(ui_text("ปิด", "Close"))
        export_btn.clicked.connect(self._on_export)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(export_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        self._load_data()

    def _load_data(self):
        self.table.setRowCount(0)
        for item in self.db.get_history(limit=200):
            row = self.table.rowCount()
            self.table.insertRow(row)
            try:
                time_text = datetime.fromisoformat(item["registered_at"]).strftime("%d/%m/%Y %H:%M")
            except Exception:
                time_text = item["registered_at"]
            values = [
                time_text,
                item["course_code"],
                item["section"],
                item["name"] or "",
                item["result"],
                item["message"] or "",
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))

    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(self, ui_text("ส่งออกประวัติ", "Export history"), os.path.expanduser("~/Desktop/history.csv"), "CSV Files (*.csv)")
        if not path:
            return
        try:
            self.db.export_registration_history_csv(path)
            QMessageBox.information(self, ui_text("ส่งออกสำเร็จ", "Export complete"), f"{ui_text('บันทึกไฟล์แล้ว', 'Saved file')}:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, ui_text("ส่งออกไม่สำเร็จ", "Export failed"), str(exc))


class MainWindow(QMainWindow):
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.browser_logged_in = False
        self.student_id = ""
        
        self.current_status_code = "disconnected"
        self.current_status_key = "not_opened"
        
        self.status_texts = {
            "not_opened": ("ยังไม่ได้เปิดเบราว์เซอร์", "Browser not open"),
            "opening": ("กำลังเปิดเบราว์เซอร์", "Opening browser..."),
            "opened_not_logged": ("เปิดเบราว์เซอร์แล้ว กรุณาล็อกอินเอง", "Browser open. Please log in manually"),
            "logged_in": ("ล็อกอินแล้ว", "Browser logged in"),
            "syncing": ("กำลังซิงก์คิวจากเว็บจริง", "Syncing real queue..."),
            "synced": ("ซิงก์คิวจากเว็บจริงแล้ว", "Real queue synced"),
            "adding_course": ("กำลังเพิ่มรายวิชา...", "Adding course..."),
            "add_done": ("เพิ่มรายวิชาเรียบร้อย", "Add course complete"),
            "waiting_room": ("พบห้องรอ", "Waiting room detected"),
            "waiting_reg": ("กำลังรอหน้าลงทะเบียน", "Waiting for registration page..."),
            "disconnected": ("ปิดเบราว์เซอร์แล้ว", "Browser closed."),
            "error_open": ("เปิดเบราว์เซอร์ไม่สำเร็จ", "Browser open failed"),
        }

        self.setStyleSheet(DARK_THEME_QSS)
        self._init_ui()
        self._init_worker()
        self.retranslate_ui()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(8)

        # 1. Top toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        
        self.open_browser_btn = QPushButton()
        self.open_browser_btn.setObjectName("accentButton")
        self.open_browser_btn.clicked.connect(self._on_open_browser)
        
        self.check_login_btn = QPushButton()
        self.check_login_btn.setEnabled(False)
        self.check_login_btn.clicked.connect(self._on_check_login)
        
        self.sync_web_btn = QPushButton()
        self.sync_web_btn.setEnabled(False)
        self.sync_web_btn.clicked.connect(self._on_sync_from_website)
        
        self.history_btn = QPushButton()
        self.history_btn.clicked.connect(self._on_show_history)
        
        # Language Selector
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("ไทย", Lang.TH)
        self.lang_combo.addItem("English", Lang.EN)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        
        toolbar.addWidget(self.open_browser_btn)
        toolbar.addWidget(self.check_login_btn)
        toolbar.addWidget(self.sync_web_btn)
        toolbar.addWidget(self.history_btn)
        toolbar.addWidget(self.lang_combo)
        toolbar.addStretch()
        
        self.student_id_label = QLabel()
        self.student_id_label.setObjectName("hintText")
        toolbar.addWidget(self.student_id_label)
        
        self.status_indicator = StatusIndicator()
        toolbar.addWidget(self.status_indicator)
        
        main_layout.addLayout(toolbar)

        # 2. Add Course Form (Group Box)
        self.manual_group = QGroupBox()
        manual_layout = QHBoxLayout()
        manual_layout.setSpacing(8)
        
        self.code_label = QLabel()
        self.code_input = QLineEdit()
        
        self.sec_label = QLabel()
        self.section_input = QLineEdit()
        self.section_input.setFixedWidth(80)
        
        self.add_course_btn = QPushButton()
        self.add_course_btn.clicked.connect(self._on_add_course)
        self.code_input.returnPressed.connect(self._on_add_course)
        self.section_input.returnPressed.connect(self._on_add_course)
        
        manual_layout.addWidget(self.code_label)
        manual_layout.addWidget(self.code_input, 1)
        manual_layout.addWidget(self.sec_label)
        manual_layout.addWidget(self.section_input)
        manual_layout.addWidget(self.add_course_btn)
        self.manual_group.setLayout(manual_layout)
        main_layout.addWidget(self.manual_group)

        # 3. Registration Queue Group
        self.queue_group = QGroupBox()
        queue_layout = QVBoxLayout()
        queue_layout.setSpacing(8)
        
        self.queue_table = RegistrationQueueTableWidget()
        self.queue_table.course_removed.connect(self._on_course_removed_from_db)
        self.queue_table.setMinimumHeight(300)
        queue_layout.addWidget(self.queue_table)

        queue_buttons = QHBoxLayout()
        queue_buttons.setSpacing(8)
        
        self.sync_queue_under_btn = QPushButton()
        self.sync_queue_under_btn.setFixedHeight(42)
        self.sync_queue_under_btn.setEnabled(False)
        self.sync_queue_under_btn.clicked.connect(self._on_sync_from_website)

        self.register_all_btn = QPushButton()
        self.register_all_btn.setObjectName("primaryButton")
        self.register_all_btn.setFixedHeight(42)
        self.register_all_btn.setEnabled(False)
        self.register_all_btn.clicked.connect(self._on_register_all)

        queue_buttons.addStretch()
        queue_buttons.addWidget(self.sync_queue_under_btn)
        queue_buttons.addWidget(self.register_all_btn)
        queue_buttons.addStretch()
        queue_layout.addLayout(queue_buttons)
        self.queue_group.setLayout(queue_layout)
        main_layout.addWidget(self.queue_group)

        # 4. Log Group
        self.log_group = QGroupBox()
        log_layout = QVBoxLayout()
        self.log_panel = LogPanel()
        log_layout.addWidget(self.log_panel)
        self.log_group.setLayout(log_layout)
        main_layout.addWidget(self.log_group)

    def _init_worker(self):
        self.worker = BrowserWorker()
        self.worker.status_update.connect(self._on_worker_status_update)
        self.worker.login_status.connect(self._on_worker_login_status)
        self.worker.student_id_update.connect(self._on_worker_student_id_update)
        self.worker.queue_synced.connect(self._on_worker_queue_synced)
        self.worker.course_result.connect(self._on_worker_course_result)
        self.worker.register_all_finished.connect(self._on_register_all_finished)
        self.worker.log_message.connect(self.log_panel.log)
        self.worker.error_occurred.connect(self._on_worker_error)
        self.worker.start()

    def _on_lang_changed(self):
        selected_lang = self.lang_combo.currentData()
        set_lang(selected_lang)
        self.retranslate_ui()

    def retranslate_ui(self):
        # Window Title
        self.setWindowTitle(f"{ui_text('ตัวช่วยลงทะเบียน MSU', 'MSU Registration Helper')} v{config.APP_VERSION}")
        
        # Toolbar
        self.open_browser_btn.setText(ui_text("เปิดเบราว์เซอร์", "Open Browser"))
        self.check_login_btn.setText(ui_text("ตรวจล็อกอิน", "Check Login"))
        self.sync_web_btn.setText(ui_text("Sync รายการจากเว็บจริง", "Sync From Website"))
        self.history_btn.setText(ui_text("ประวัติ", "History"))
        
        self._update_student_id_label()
        self._update_status_indicator()
        
        # Add Course
        self.manual_group.setTitle(ui_text("เพิ่มรายวิชา", "Add Course"))
        self.code_label.setText(ui_text("รหัสวิชา", "Course code"))
        self.sec_label.setText(ui_text("กลุ่ม", "Section"))
        self.code_input.setPlaceholderText(ui_text("เช่น 0041001", "e.g. 0041001"))
        self.section_input.setPlaceholderText(ui_text("เช่น 1", "e.g. 1"))
        self.add_course_btn.setText(ui_text("เพิ่มรายวิชา", "Add Course"))
        
        # Queue Table
        self.queue_group.setTitle(ui_text("คิวลงทะเบียนจริง (ดึงจาก confirm_enroll.asp)", "Registration Queue (confirm_enroll.asp)"))
        self.sync_queue_under_btn.setText(ui_text("Sync คิวจากเว็บจริง", "Sync Queue From Website"))
        self.register_all_btn.setText(ui_text("ยืนยันการลงทะเบียน", "Confirm Registration"))
        self.queue_table.refresh_lang()
        
        # Reload queue rows
        self._load_courses_from_db()
        
        # Log
        self.log_group.setTitle(ui_text("บันทึกการทำงาน", "Log"))

    def _update_student_id_label(self):
        if self.student_id:
            self.student_id_label.setText(f"{ui_text('รหัสนศ.:', 'Student ID:')} {self.student_id}")
        else:
            self.student_id_label.setText(ui_text("รหัสนศ.: -", "Student ID: -"))

    def _update_status_indicator(self):
        th, en = self.status_texts.get(self.current_status_key, ("", ""))
        self.status_indicator.set_status(self.current_status_code, th if get_lang() == Lang.TH else en)

    def _load_courses_from_db(self):
        self.queue_table.clear_all()
        for course in self.db.get_courses():
            self.queue_table.add_course_row(course)
        self._update_register_button_state()

    def _update_register_button_state(self):
        # Enable Confirm Registration if logged in and we have pending rows
        has_pending_items = any(course.status == CourseStatus.PENDING for course in self.db.get_courses())
        self.register_all_btn.setEnabled(self.browser_logged_in and has_pending_items)

    def _on_open_browser(self):
        self.worker.submit_command("open_browser")
        self.open_browser_btn.setEnabled(False)

    def _on_check_login(self):
        self.worker.submit_command("check_login")

    def _on_sync_from_website(self):
        self.worker.submit_command("sync_queue")

    def _on_show_history(self):
        HistoryDialog(self.db, self).exec()

    def _on_add_course(self):
        code = self.code_input.text().strip()
        sec = self.section_input.text().strip()
        if not code or not sec:
            QMessageBox.warning(self, ui_text("ข้อมูลไม่ครบ", "Missing data"), ui_text("กรุณากรอกรหัสวิชาและกลุ่มเรียน", "Course code and section are required."))
            return
        self.add_course_btn.setEnabled(False)
        self.worker.submit_command("add_course", course_code=code, section=sec)

    def _on_course_removed_from_db(self, course_id: int):
        self.db.remove_course(course_id)
        self._load_courses_from_db()

    def _on_register_all(self):
        self.register_all_btn.setEnabled(False)
        self.worker.submit_command("register_all")

    def _on_worker_status_update(self, status_code: str, status_key: str):
        self.current_status_code = status_code
        self.current_status_key = status_key
        self._update_status_indicator()
        
        if status_code == "connected":
            self.check_login_btn.setEnabled(True)
            self.sync_web_btn.setEnabled(True)
            self.sync_queue_under_btn.setEnabled(True)
            self.open_browser_btn.setEnabled(False)
        elif status_code == "disconnected":
            self.check_login_btn.setEnabled(False)
            self.sync_web_btn.setEnabled(False)
            self.sync_queue_under_btn.setEnabled(False)
            self.open_browser_btn.setEnabled(True)
            self.browser_logged_in = False
            self.student_id = ""
            self._update_student_id_label()
            self._update_register_button_state()

    def _on_worker_login_status(self, is_logged: bool):
        self.browser_logged_in = is_logged
        if is_logged:
            self.current_status_code = "connected"
            self.current_status_key = "logged_in"
        else:
            self.current_status_code = "connected"
            self.current_status_key = "opened_not_logged"
            self.student_id = ""
            self._update_student_id_label()
            
        self._update_status_indicator()
        self._update_register_button_state()

    def _on_worker_student_id_update(self, student_id: str):
        self.student_id = student_id
        self._update_student_id_label()

    def _on_worker_queue_synced(self, rows: list[dict]):
        self.db.replace_courses_from_web(rows)
        self.add_course_btn.setEnabled(True)
        self.code_input.clear()
        self.section_input.clear()
        self._load_courses_from_db()

    def _on_worker_error(self, err_msg: str):
        self.add_course_btn.setEnabled(True)
        QMessageBox.warning(self, ui_text("ผลการทำงาน", "Operation Result"), err_msg)

    def _on_worker_course_result(self, result: dict):
        db_id = result.get("db_id")
        if db_id is None:
            return
        status = normalize_status(result.get("status", CourseStatus.FAILED.value))
        message = result.get("message", "")
        name = result.get("name", "")
        try:
            status_enum = CourseStatus(status)
        except ValueError:
            status_enum = CourseStatus.FAILED
            status = status_enum.value

        self.db.update_course_status(db_id, status, message)
        if name:
            self.db.update_course_name(db_id, name)
        self.queue_table.update_row_status(db_id, status_enum, name=name, message=message)
        self.db.save_registration_result(
            profile_id=None,
            saved_course_id=None,
            course_code=result["course_code"],
            section=result["section"],
            name=name,
            result=status,
            message=message,
            action=result.get("action", CourseAction.ADD.value),
        )
        self.log_panel.log(f"{result['course_code']} Sec {result['section']} -> {status}: {message}", "success" if status in {"pending", "success"} else "warning")

    def _on_register_all_finished(self):
        self._update_register_button_state()
        QMessageBox.information(
            self,
            ui_text("ยืนยันเสร็จแล้ว", "Confirm finished"),
            ui_text("ระบบส่งคำสั่งยืนยันบนเว็บจริงแล้ว และซิงก์คิวล่าสุดกลับมาแสดง", "The app sent the confirm action on the real page and synced the latest queue."),
        )

    def closeEvent(self, event):
        self.worker.running = False
        self.worker.submit_command("close_all")
        self.worker.wait()
        event.accept()
