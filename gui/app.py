"""
MSU Registration Helper — Main Application Window
ส่วนติดต่อผู้ใช้หลักและระบบการสื่อสารผ่าน QThread สำหรับควบคุม Playwright
"""

import os
import queue
import time
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QDialog,
    QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox,
    QHeaderView, QComboBox
)
from PyQt6.QtCore import pyqtSignal, QThread, Qt

import config
from models.course import Course, CourseStatus, CourseAction
from database.db import DatabaseManager
from automation.browser import BrowserController
from automation.register import RegistrationService
from gui.styles import DARK_THEME_QSS
from gui.widgets import CourseTableWidget, LogPanel, StatusIndicator


class BrowserWorker(QThread):
    """
    QThread สำหรับควบคุม Playwright เบื้องหลัง
    หลีกเลี่ยงการทำให้หน้าจอ GUI ค้าง (Non-blocking GUI)
    """
    # Signals สำหรับส่งข้อมูลกลับหน้า GUI หลัก
    status_update = pyqtSignal(str, str) # status_code, display_text
    login_status = pyqtSignal(bool)
    course_result = pyqtSignal(dict) # ข้อมูลผลลัพธ์รายวิชา
    confirm_result = pyqtSignal(bool, list) # ผลการยืนยันทั้งหมด
    log_message = pyqtSignal(str, str) # message, log_level
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.cmd_queue = queue.Queue()
        self.browser: Optional[BrowserController] = None
        self.register_service = Optional[RegistrationService]
        self.running = True

    def run(self):
        """ลูปหลักการรับคำสั่งจากคิว"""
        self.log_message.emit("ระบบนำส่งข้อมูลบราวเซอร์พร้อมใช้งาน", "system")
        self.browser = BrowserController()
        
        while self.running:
            try:
                # ตรวจสอบคำสั่งในคิว (รอกล่องคำสั่งสูงสุด 1 วินาที)
                cmd_data = self.cmd_queue.get(timeout=1.0)
                cmd_type = cmd_data.get("type")
                
                if cmd_type == "open_browser":
                    self._handle_open_browser()
                elif cmd_type == "check_login":
                    self._handle_check_login()
                elif cmd_type == "add_course":
                    self._handle_add_course(cmd_data["course_db_id"], cmd_data["code"], cmd_data["section"], cmd_data.get("action", "add"))
                elif cmd_type == "confirm":
                    self._handle_confirm()
                elif cmd_type == "close_all":
                    self._handle_close()
                    break
                    
                self.cmd_queue.task_done()
                
            except queue.Empty:
                # ในกรณีที่คิวว่างเปล่า: ให้เฝ้าระวัง session หรือ keep alive ทุกๆ ช่วงเวลา
                if self.browser and self.browser.is_open:
                    # เช็คสถานะ waiting room
                    if self.browser.detect_waiting_room():
                        self.status_update.emit("waiting", "ติดหน้าคิว (Cloudflare Waiting Room)...")
                        # รอจนหน้าเว็บพร้อมใช้งานแบบเงียบๆ
                        ready_status = self.browser.wait_for_page_ready(timeout_seconds=10)
                        if ready_status == "ready":
                            self.status_update.emit("connected", "เบราว์เซอร์พร้อมใช้งาน")
                            self.log_message.emit("พ้นคิวรอตรวจจับแล้ว หน้าเว็บพร้อมเข้าใช้งาน", "success")
                    
                    # ตรวจสอบล็อกอิน
                    is_logged = self.browser.is_logged_in()
                    self.login_status.emit(is_logged)
                    
                    # ทำ keep alive เบาๆ ป้องกัน session หลุด
                    self.browser.keep_alive()

            except Exception as e:
                self.log_message.emit(f"เกิดข้อผิดพลาดในการรันคำสั่ง: {str(e)}", "error")
                self.error_occurred.emit(str(e))

    def submit_command(self, cmd_type: str, **kwargs):
        """ส่งคำสั่งเข้าคิวงานของ Thread"""
        cmd = {"type": cmd_type}
        cmd.update(kwargs)
        self.cmd_queue.put(cmd)

    def _handle_open_browser(self):
        """คำสั่งเปิดเบราว์เซอร์"""
        self.log_message.emit("กำลังเปิดเบราว์เซอร์...", "info")
        self.status_update.emit("waiting", "กำลังเปิดเบราว์เซอร์...")
        
        try:
            page = self.browser.open_browser()
            self.register_service = RegistrationService(page)
            
            # บันทึกสถานะว่าเปิดหน้าสำเร็จ
            self.status_update.emit("connected", "เปิดบราวเซอร์สำเร็จ (รอผู้ใช้เข้าสู่ระบบ)")
            self.log_message.emit("เปิดเบราว์เซอร์สำเร็จ กรุณาเข้าระบบในหน้าเบราว์เซอร์", "success")
            
            # เช็คว่าล็อกอินค้างจาก Session เดิมหรือไม่
            is_logged = self.browser.is_logged_in()
            self.login_status.emit(is_logged)
            if is_logged:
                self.log_message.emit("พบเซสชันการเข้าระบบเดิม ลงทะเบียนอัตโนมัติได้ทันที", "success")
                
        except Exception as e:
            self.status_update.emit("error", "เปิดบราวเซอร์ล้มเหลว")
            self.log_message.emit(f"ไม่สามารถเปิดเบราว์เซอร์ได้: {str(e)}", "error")
            # ถ่ายภาพไว้เป็นหลักฐาน
            self.browser.take_screenshot("browser_open_error")

    def _handle_check_login(self):
        """เช็คสถานะการเข้าสู่ระบบปัจจุบัน"""
        if not self.browser or not self.browser.is_open:
            self.log_message.emit("กรุณาเปิดบราวเซอร์ก่อนตรวจสอบสิทธิ์", "warning")
            return
            
        try:
            is_logged = self.browser.is_logged_in()
            self.login_status.emit(is_logged)
            if is_logged:
                self.log_message.emit("ตรวจสอบสำเร็จ: ลงชื่อเข้าใช้แล้ว", "success")
                self.status_update.emit("connected", "พร้อมลงทะเบียนเรียน")
            else:
                self.log_message.emit("ตรวจสอบสิทธิ์: ยังไม่ได้เข้าสู่ระบบหรือกำลังล็อกอิน", "warning")
        except Exception as e:
            self.log_message.emit(f"เกิดข้อผิดพลาดขณะตรวจสิทธิ์: {str(e)}", "error")

    def _handle_add_course(self, course_db_id: int, code: str, section: str, action: str = "add"):
        """ทำรายการกรอกรหัสและ sec เพื่อเพิ่มเข้าหน้าเว็บ หรือลดรายวิชาออก"""
        if not self.browser or not self.browser.is_open:
            self.log_message.emit(f"ไม่สามารถทำรายการวิชา {code} ได้: ยังไม่ได้เปิดบราวเซอร์", "error")
            self.course_result.emit({"db_id": course_db_id, "status": "unknown", "message": "ไม่ได้เชื่อมบราวเซอร์"})
            return
            
        if not self.browser.is_logged_in():
            self.log_message.emit(f"ไม่สามารถทำรายการวิชา {code} ได้: ยังไม่ได้เข้าระบบ", "warning")
            self.course_result.emit({"db_id": course_db_id, "status": "unknown", "message": "กรุณาเข้าระบบก่อน"})
            return

        try:
            # 1. เช็ค Waiting Room
            if self.browser.detect_waiting_room():
                self.log_message.emit("ตรวจพบ Cloudflare Waiting Room กำลังรอคิวเพื่อทำงานต่อ...", "warning")
                self.status_update.emit("waiting", "ติดหน้าคิว (Cloudflare)...")
                ready_status = self.browser.wait_for_page_ready(timeout_seconds=120) # รอนานขึ้น
                if ready_status != "ready":
                    self.log_message.emit("การรอคิวหมดเวลาก่อนระบบพร้อมทำงาน", "error")
                    self.course_result.emit({"db_id": course_db_id, "status": "unknown", "message": "คิวหมดเวลา"})
                    return
                self.status_update.emit("connected", "พร้อมลงทะเบียนเรียน")

            # 2. นำทางเข้าสู่หน้าลงทะเบียนเรียน
            self.log_message.emit(f"กำลังไปที่หน้าลงทะเบียนเพื่อทำรายการวิชา {code} Sec {section}...", "info")
            self.register_service.navigate_to_register()
            
            # 3. สั่งทำธุรกรรมตามประเภท (ลงทะเบียน / ลดรายวิชา)
            if action == "drop":
                self.log_message.emit(f"กำลังลดวิชา {code} Sec {section} ออกจากตารางเว็บ...", "info")
                res = self.register_service.drop_course(code, section)
            else:
                self.log_message.emit(f"กำลังเพิ่มวิชา {code} Sec {section} ลงในตารางเว็บ...", "info")
                res = self.register_service.retry_add_course(code, section)
            
            # 4. ส่งผลลัพธ์
            res["db_id"] = course_db_id
            self.course_result.emit(res)
            
            log_level = "success" if res["status"] == "pending" else "error"
            action_text = "ลดวิชา" if action == "drop" else "เพิ่มวิชา"
            self.log_message.emit(f"ผลลัพธ์{action_text} {code} Sec {section} ▸ {res['message']}", log_level)
            
            if res["status"] not in ["pending", "success"]:
                # ถ้าไม่สำเร็จ แคปเจอร์หน้าจอไว้ดู
                screenshot_path = self.browser.take_screenshot(f"fail_{action}_{code}_{section}")
                if screenshot_path:
                    self.log_message.emit(f"บันทึกรูปหลักฐานความผิดพลาดที่: {os.path.basename(screenshot_path)}", "info")

        except Exception as e:
            self.log_message.emit(f"เกิดข้อผิดพลาดขณะทำรายการ {code}: {str(e)}", "error")
            self.course_result.emit({"db_id": course_db_id, "status": "unknown", "message": str(e)})
            self.browser.take_screenshot(f"err_{action}_{code}_{section}")

    def _handle_confirm(self):
        """กดยืนยันบันทึกข้อมูลหน้าเว็บลงทะเบียนจริง"""
        if not self.browser or not self.browser.is_open:
            self.log_message.emit("เบราว์เซอร์ยังไม่ได้เปิดการทำงาน", "error")
            return

        try:
            self.log_message.emit("กำลังส่งคำสั่งยืนยันการลงทะเบียนเรียน...", "info")
            ok = self.register_service.confirm_registration()
            
            if ok:
                time.sleep(2) # รอโหลดหน้าสรุปผลลัพธ์
                results = self.register_service.read_results()
                self.confirm_result.emit(True, results)
                self.log_message.emit("กดยืนยันการลงทะเบียนเรียบร้อยแล้ว! ผลลัพธ์สรุปกลับมาแล้ว", "success")
            else:
                self.confirm_result.emit(False, [])
                self.log_message.emit("ยืนยันไม่สำเร็จ (ปุ่มกดอาจจะถูกปิดการทำงานในขณะนั้น)", "warning")
                self.browser.take_screenshot("confirm_failed")
                
        except Exception as e:
            self.log_message.emit(f"เกิดข้อผิดพลาดขณะกดยืนยัน: {str(e)}", "error")
            self.confirm_result.emit(False, [])
            self.browser.take_screenshot("confirm_exception")

    def _handle_close(self):
        """ปิดเบราว์เซอร์"""
        if self.browser:
            self.log_message.emit("กำลังปิดเบราว์เซอร์และ Playwright...", "system")
            self.browser.close()
            self._is_open = False
            self.status_update.emit("disconnected", "เบราว์เซอร์ถูกปิดแล้ว")


class HistoryDialog(QDialog):
    """
    หน้าต่างป็อปอัปแสดงประวัติการลงทะเบียนเรียนจาก Database
    """
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("📜 ประวัติการลงทะเบียนเรียน")
        self.resize(700, 500)
        self.setStyleSheet(DARK_THEME_QSS)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # ตารางประวัติ
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["เวลา", "รหัสวิชา", "หมู่เรียน", "ชื่อวิชา", "ผลลัพธ์", "รายละเอียด"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.table)
        
        # ปุ่มควบคุม
        btn_layout = QHBoxLayout()
        export_btn = QPushButton("📊 ส่งออก CSV")
        export_btn.clicked.connect(self._on_export)
        close_btn = QPushButton("ปิด")
        close_btn.clicked.connect(self.close)
        
        btn_layout.addWidget(export_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self._load_data()

    def _load_data(self):
        """โหลดข้อมูลประวัติจาก Database"""
        histories = self.db.get_history(limit=100)
        self.table.setRowCount(0)
        
        for h in histories:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # จัดรูปแบบเวลาจาก ISO format
            reg_time = h["registered_at"]
            try:
                dt = datetime.fromisoformat(reg_time)
                time_str = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                time_str = reg_time
                
            self.table.setItem(row, 0, QTableWidgetItem(time_str))
            
            code_item = QTableWidgetItem(h["course_code"])
            code_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, code_item)
            
            sec_item = QTableWidgetItem(h["section"])
            sec_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, sec_item)
            
            self.table.setItem(row, 3, QTableWidgetItem(h["name"] or ""))
            
            # ผลลัพธ์ (แปลงสถานะ)
            status_text = h["result"]
            try:
                status_enum = CourseStatus(status_text)
                disp_text = status_enum.display_text
            except ValueError:
                disp_text = status_text
                
            self.table.setItem(row, 4, QTableWidgetItem(disp_text))
            
            # ประเภททำรายการและข้อความเตือน
            action_text = "ลดวิชา" if h.get("action") == "drop" else "ลงทะเบียน"
            detail_msg = f"[{action_text}] {h['message']}" if h['message'] else f"[{action_text}]"
            self.table.setItem(row, 5, QTableWidgetItem(detail_msg))

    def _on_export(self):
        """ส่งออกประวัติเป็นไฟล์ CSV"""
        path, _ = QFileDialog.getSaveFileName(
            self, "บันทึกข้อมูลประวัติ", os.path.expanduser("~/Desktop"), "CSV Files (*.csv)"
        )
        if path:
            try:
                self.db.export_csv(path)
                QMessageBox.information(self, "สำเร็จ", f"ส่งออกประวัติลงทะเบียนเรียนไปที่:\n{path} สำเร็จ")
            except Exception as e:
                QMessageBox.critical(self, "ล้มเหลว", f"เกิดปัญหาในการส่งออกไฟล์ CSV:\n{str(e)}")


class MainWindow(QMainWindow):
    """
    หน้าต่าง GUI หลักของระบบ MSU Registration Helper
    """
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.db = db
        self.browser_logged_in = False
        
        self.setWindowTitle(f"🎓 {config.APP_NAME} v{config.APP_VERSION}")
        self.resize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        self.setStyleSheet(DARK_THEME_QSS)
        
        self._init_ui()
        self._init_worker()
        self._load_courses_from_db()

    def _init_ui(self):
        """โครงสร้าง Layout หน้าจอหลัก"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # 1. ส่วนควบคุมหลัก Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.open_browser_btn = QPushButton("🌐 เปิด Browser")
        self.open_browser_btn.setObjectName("accentButton")
        self.open_browser_btn.clicked.connect(self._on_open_browser)
        
        self.check_login_btn = QPushButton("✅ เช็ค Login")
        self.check_login_btn.clicked.connect(self._on_check_login)
        self.check_login_btn.setEnabled(False)
        
        self.history_btn = QPushButton("📊 ดูประวัติ")
        self.history_btn.clicked.connect(self._on_show_history)
        
        toolbar_layout.addWidget(self.open_browser_btn)
        toolbar_layout.addWidget(self.check_login_btn)
        toolbar_layout.addWidget(self.history_btn)
        toolbar_layout.addStretch()
        
        # ดวงไฟสถานะบราวเซอร์
        self.status_indicator = StatusIndicator()
        toolbar_layout.addWidget(self.status_indicator)
        
        main_layout.addLayout(toolbar_layout)

        # 2. ฟอร์มเพิ่มรหัสวิชาแบบด่วน
        form_group = QGroupBox("➕ เพิ่มวิชาเข้าคิวเพื่อเตรียมลงทะเบียน")
        form_layout = QHBoxLayout()
        form_layout.setContentsMargins(15, 15, 15, 15)
        
        form_layout.addWidget(QLabel("รหัสวิชา:"))
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("เช่น 0041001")
        self.code_input.setMaxLength(10)
        form_layout.addWidget(self.code_input)
        
        form_layout.addWidget(QLabel("หมู่เรียน (Sec):"))
        self.sec_input = QLineEdit()
        self.sec_input.setPlaceholderText("เช่น 1")
        self.sec_input.setMaxLength(4)
        form_layout.addWidget(self.sec_input)
        
        form_layout.addWidget(QLabel("ประเภท:"))
        self.action_input = QComboBox()
        self.action_input.addItem("➕ ลงทะเบียน", CourseAction.ADD)
        self.action_input.addItem("➖ ลดรายวิชา", CourseAction.DROP)
        form_layout.addWidget(self.action_input)
        
        self.add_course_btn = QPushButton("เพิ่มลงรายการ")
        self.add_course_btn.clicked.connect(self._on_add_course_to_queue)
        form_layout.addWidget(self.add_course_btn)
        
        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)
        
        # ดักจับการกด Enter ในฟิลด์กรอก Sec เพื่อเพิ่มวิชาทันที (One-key submit)
        self.sec_input.returnPressed.connect(self._on_add_course_to_queue)

        # 3. รายการตารางวิชา
        queue_group = QGroupBox("📋 ตารางรายวิชาลงทะเบียนเตรียมระบบกรอก")
        queue_layout = QVBoxLayout()
        queue_layout.setContentsMargins(10, 15, 10, 10)
        
        self.course_table = CourseTableWidget()
        self.course_table.course_removed.connect(self._on_course_removed_from_db)
        queue_layout.addWidget(self.course_table)
        
        # ปุ่มยืนยันยิงลงทะเบียนสุดท้าย
        confirm_btn_layout = QHBoxLayout()
        self.confirm_reg_btn = QPushButton("✔️ ยืนยันการลงทะเบียนเรียนทั้งหมด")
        self.confirm_reg_btn.setObjectName("primaryButton")
        self.confirm_reg_btn.setFixedHeight(42)
        self.confirm_reg_btn.setEnabled(False)
        self.confirm_reg_btn.clicked.connect(self._on_confirm_registration)
        confirm_btn_layout.addStretch()
        confirm_btn_layout.addWidget(self.confirm_reg_btn)
        confirm_btn_layout.addStretch()
        
        queue_layout.addLayout(confirm_btn_layout)
        queue_group.setLayout(queue_layout)
        main_layout.addWidget(queue_group)

        # 4. แผงควบคุม Log
        log_group = QGroupBox("📝 บันทึกประวัติการทำงานระบบ")
        log_layout = QVBoxLayout()
        log_layout.setContentsMargins(10, 15, 10, 10)
        
        self.log_panel = LogPanel()
        log_layout.addWidget(self.log_panel)
        
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)
        
        # แสดง Log เริ่มต้น
        self.log_panel.log("ยินดีต้อนรับเข้าสู่ MSU Registration Helper", "system")
        self.log_panel.log("พร้อมช่วยเหลืออำนวยความสะดวกในการลงทะเบียนเรียน", "info")

    def _init_worker(self):
        """เริ่มกระบวนการ Worker Thread"""
        self.worker = BrowserWorker()
        
        # เชื่อมสัญญาณ Signals/Slots
        self.worker.status_update.connect(self._on_worker_status_update)
        self.worker.login_status.connect(self._on_worker_login_status)
        self.worker.course_result.connect(self._on_worker_course_result)
        self.worker.confirm_result.connect(self._on_worker_confirm_result)
        self.worker.log_message.connect(self.log_panel.log)
        self.worker.error_occurred.connect(lambda e: QMessageBox.critical(self, "เกิดข้อผิดพลาดเบื้องหลัง", e))
        
        self.worker.start()

    def _load_courses_from_db(self):
        """ดึงคิววิชาเดิมที่บันทึกไว้ใน SQLite มาขึ้นตาราง"""
        courses = self.db.get_courses()
        self.course_table.clear_all()
        for course in courses:
            self.course_table.add_course_row(course)
        
        # ตรวจสอบปุ่มยืนยัน
        self._update_confirm_button_state()

    def _update_confirm_button_state(self):
        """ตรวจสอบความพร้อมปุ่มบันทึกใหญ่ (เมื่อมีอย่างน้อย 1 วิชาที่เป็น pending หรือ success)"""
        courses = self.db.get_courses()
        has_pending = any(c.status == CourseStatus.PENDING for c in courses)
        self.confirm_reg_btn.setEnabled(has_pending and self.browser_logged_in)

    # ─── Slots & Event Handlers ──────────────────────────────────

    def _on_open_browser(self):
        """เมื่อผู้ใช้กดเปิดเบราว์เซอร์"""
        self.worker.submit_command("open_browser")
        self.open_browser_btn.setEnabled(False)

    def _on_check_login(self):
        """ตรวจสอบการเข้าระบบ"""
        self.worker.submit_command("check_login")

    def _on_show_history(self):
        """เปิดประวัติย้อนหลัง"""
        dialog = HistoryDialog(self.db, self)
        dialog.exec()

    def _on_add_course_to_queue(self):
        """เมื่อผู้ใช้สั่งแอดวิชาใหม่"""
        code = self.code_input.text().strip()
        sec = self.sec_input.text().strip()
        action = self.action_input.currentData() # ดึงค่า CourseAction enum
        
        if not code or not sec:
            self.log_panel.log("กรุณากรอกรหัสวิชาและหมู่เรียนให้ครบถ้วน", "warning")
            return
            
        # ตรวจสอบว่าแอดซ้ำในรายการตารางปัจจุบันหรือไม่
        existing_courses = self.course_table.get_all_courses()
        is_dup = any(c["course_code"] == code and c["section"] == sec for c in existing_courses)
        if is_dup:
            self.log_panel.log(f"วิชา {code} Sec {sec} มีอยู่ในตารางพร้อมดำเนินการแล้ว", "warning")
            return

        # 1. สร้างวัตถุ Course สภาพอยู่ในคิว (QUEUED)
        new_course = Course(
            course_code=code,
            section=sec,
            action=action,
            status=CourseStatus.QUEUED
        )
        
        # 2. บันทึกลง SQLite
        db_id = self.db.add_course(new_course)
        new_course.id = db_id
        
        # 3. อัปเดตตาราง GUI
        self.course_table.add_course_row(new_course)
        
        action_name = "ลดวิชา" if action == CourseAction.DROP else "ลงทะเบียน"
        self.log_panel.log(f"เพิ่มรายการ {action_name} วิชา {code} Sec {sec} ลงคิวสำเร็จ", "info")
        
        # เคลียร์ช่องป้อนและ Focus ไปที่เดิมเพื่อสะดวกแก่การป้อนถัดไป
        self.code_input.clear()
        self.sec_input.clear()
        self.code_input.setFocus()

        # 4. หากบราวเซอร์เชื่อมต่ออยู่แล้ว ให้ระบบดำเนินการทันทีแบบ Auto!
        if self.worker.browser and self.worker.browser.is_open and self.browser_logged_in:
            # อัปเดตสถานะเป็น pending ชั่วคราวเพื่อรอผลลัพธ์
            self.db.update_course_status(db_id, CourseStatus.PENDING.value, "กำลังทำรายการ...")
            self.course_table.update_row_status(db_id, CourseStatus.PENDING)
            
            # ส่งคำสั่งให้ Playwright กรอกวิชาลงเว็บจริง
            self.worker.submit_command("add_course", course_db_id=db_id, code=code, section=sec, action=action.value)

    def _on_course_removed_from_db(self, course_id: int):
        """ลบวิชาออกจาก SQLite เมื่อกดปุ่มลบในตาราง"""
        self.db.remove_course(course_id)
        self.log_panel.log(f"นำวิชาลำดับ {course_id} ออกจากคิวแล้ว", "warning")
        self._update_confirm_button_state()

    def _on_confirm_registration(self):
        """ยืนยันการลงทะเบียน (คลิกปุ่มบันทึกใหญ่ของบราวเซอร์เพื่อตัดผลสุดท้าย)"""
        reply = QMessageBox.question(
            self, 
            "ยืนยันขั้นตอนสุดท้าย", 
            "ต้องการยืนยันการลงทะเบียนเรียนทั้งหมดที่บันทึกค้างไว้หรือไม่?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.confirm_reg_btn.setEnabled(False)
            self.worker.submit_command("confirm")

    # ─── Worker Signals Handlers ────────────────────────────────

    def _on_worker_status_update(self, status_code: str, display_text: str):
        """อัปเดตสถานะ Indicator หน้าแอป"""
        self.status_indicator.set_status(status_code, display_text)
        
        if status_code == "connected":
            self.check_login_btn.setEnabled(True)
            self.open_browser_btn.setEnabled(False)
        elif status_code == "disconnected":
            self.check_login_btn.setEnabled(False)
            self.open_browser_btn.setEnabled(True)
            self.browser_logged_in = False
            self._update_confirm_button_state()

    def _on_worker_login_status(self, is_logged: bool):
        """อัปเดตสถานะการตรวจสอบสิทธิ์ล็อกอิน"""
        self.browser_logged_in = is_logged
        
        if is_logged:
            self.status_indicator.set_status("connected", "เบราว์เซอร์: ล็อกอินเข้าระบบแล้ว")
            
            # เมื่อพบว่าล็อกอินสำเร็จ ให้ประมวลผลวิชาในคิวที่ยังเป็น QUEUED โดยการกรอกให้อัตโนมัติทันที
            courses = self.db.get_courses()
            for c in courses:
                if c.status == CourseStatus.QUEUED:
                    self.db.update_course_status(c.id, CourseStatus.PENDING.value, "กำลังยิงข้อมูลออโต้...")
                    self.course_table.update_row_status(c.id, CourseStatus.PENDING)
                    self.worker.submit_command("add_course", course_db_id=c.id, code=c.course_code, section=c.section, action=c.action.value)
        else:
            self.status_indicator.set_status("connected", "เปิดบราวเซอร์สำเร็จ (รอเข้าสู่ระบบ)")
            
        self._update_confirm_button_state()

    def _on_worker_course_result(self, res: dict):
        """เมื่อประมวลผลเพิ่มรายวิชารายบรรทัดสำเร็จ"""
        db_id = res["db_id"]
        status_str = res["status"]
        message = res["message"]
        name = res.get("name", "")
        
        try:
            status_enum = CourseStatus(status_str)
        except ValueError:
            status_enum = CourseStatus.UNKNOWN
            
        # 1. บันทึกผลอัปเดตลง Database
        self.db.update_course_status(db_id, status_str, message)
        if name:
            # อัปเดตชื่อวิชาใน SQLite
            with self.db._get_connection() as conn:
                conn.cursor().execute("UPDATE courses SET name = ? WHERE id = ?", (name, db_id))
        
        # 2. ปรับปรุงสถานะตารางในหน้า GUI
        self.course_table.update_row_status(db_id, status_enum, name=name, message=message)
        
        # 3. อัปเดตปุ่มยืนยัน
        self._update_confirm_button_state()

    def _on_worker_confirm_result(self, success: bool, results: list):
        """หลังจากทำการ Confirm บันทึกชุดลงทะเบียนแล้ว"""
        if not success:
            QMessageBox.warning(self, "ผลลัพธ์ลงทะเบียน", "ยืนยันผลการลงทะเบียนไม่สำเร็จ กรุณาตรวจสอบบนหน้าเว็บบราวเซอร์")
            self._update_confirm_button_state()
            return
            
        # อัปเดตประวัติทั้งหมดลง SQLite
        courses = self.db.get_courses()
        
        for c in courses:
            # ค้นหารายวิชาในผลสรุปเพจจริง เพื่อความถูกต้องสูงสุด
            page_status_str = "success"
            page_msg = "ลงทะเบียนสำเร็จ"
            
            for r in results:
                if r["course_code"] == c.course_code and r["section"] == c.section:
                    res_val = r["result"]
                    page_msg = r["result"]
                    if "สำเร็จ" in res_val:
                        page_status_str = "success"
                    elif "เต็ม" in res_val:
                        page_status_str = "full"
                    elif "ชน" in res_val:
                        page_status_str = "conflict"
                    else:
                        page_status_str = "unknown"
                    break
            
            # บันทึกลงตารางประวัติ (History Table)
            history_course = Course(
                course_code=c.course_code,
                section=c.section,
                name=c.name or "ไม่ระบุชื่อวิชา",
                action=c.action,
                status=CourseStatus(page_status_str),
                message=page_msg
            )
            self.db.add_history(history_course)
            
        # เคลียร์ล้างคิวงานชั่วคราว
        self.db.clear_courses()
        self.course_table.clear_all()
        
        QMessageBox.information(
            self, 
            "ลงทะเบียนเสร็จสิ้น", 
            f"ดำเนินการลงทะเบียนเรียบร้อย! คิวรันระบบเสร็จสิ้น ระบบบันทึกประวัติไว้เรียบร้อยแล้ว {len(courses)} รายการ"
        )
        self.log_panel.log("การลงทะเบียนคิวปัจจุบันเสร็จสิ้น ประวัติถูกบันทึกเรียบร้อย", "success")
        self._update_confirm_button_state()

    def closeEvent(self, event):
        """เมื่อปิดแอปพลิเคชันหลัก ดับโปรเจ็กต์ Playwright Gracefully"""
        self.worker.running = False
        self.worker.submit_command("close_all")
        self.worker.wait() # รอจนกว่าเธรดเบื้องหลังจะปิดตัวสมบูรณ์
        event.accept()
