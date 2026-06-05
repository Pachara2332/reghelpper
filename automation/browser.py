"""
MSU Registration Helper — Browser Controller
ควบคุม Browser ด้วย Playwright สำหรับเฝ้าระวัง Waiting room และเข้าสู่หน้าเว็บลงทะเบียน
"""

import os
import time
from datetime import datetime
from typing import Optional
from playwright.sync_api import sync_playwright, BrowserContext, Page, Error

import config

class BrowserController:
    """
    ควบคุมการทำงานของ Playwright Browser
    และตรวจจับสถานะหน้าเว็บ (Waiting Room, Server Error)
    """

    def __init__(self):
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._is_open = False

    @property
    def is_open(self) -> bool:
        """ตรวจสอบว่าเบราว์เซอร์ยังเปิดอยู่หรือไม่"""
        return self._is_open and self.page is not None

    def open_browser(self) -> Page:
        """
        เปิด Chromium browser ด้วย persistent context (เพื่อจดจำ session/login)
        """
        if self.is_open:
            return self.page

        self.playwright = sync_playwright().start()
        
        # ตั้งค่า Chromium options
        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir=config.BROWSER_PROFILE_DIR,
            headless=False,
            viewport=None,  # ใช้ default size
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled"  # ป้องกันการตรวจจับ bot เบื้องต้น
            ]
        )
        
        # ตั้งค่า default timeout
        self.context.set_default_timeout(30000) # 30 วินาที
        
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self._is_open = True
        
        # ไปหน้าล็อกอินเริ่มต้น
        urls = config.get_urls()
        self.navigate_to(urls["login"])
        
        return self.page

    def navigate_to(self, url: str):
        """ไปยัง URL ที่กำหนด"""
        if not self.is_open:
            raise RuntimeError("เบราว์เซอร์ยังไม่ได้เปิดการทำงาน")
        try:
            self.page.goto(url, wait_until="load")
        except Error as e:
            print(f"Error navigating to {url}: {e}")

    def get_page_content(self) -> str:
        """ดึง HTML Content ของหน้าปัจจุบัน"""
        if not self.is_open:
            return ""
        try:
            return self.page.content()
        except Error:
            return ""

    def is_logged_in(self) -> bool:
        """
        ตรวจสอบว่าล็อกอินสำเร็จหรือไม่
        - ใน Demo mode: เช็คจาก URL ว่าไม่ได้อยู่หน้า index.html หรือ login
        - ใน Prod mode: เช็คจากหน้าเว็บจริง
        """
        if not self.is_open:
            return False
        
        current_url = self.page.url.lower()
        
        if config.MODE == "demo":
            # ถ้าอยู่ใน dashboard หรือ register หรือ result แปลว่า logged in แล้ว
            # และต้องไม่อยู่ใน index.html
            return "index.html" not in current_url and (
                "dashboard.html" in current_url or 
                "register.html" in current_url or 
                "result.html" in current_url
            )
        else:
            # สำหรับเว็บจริง (เช็คว่าไม่มีปุ่ม/ช่อง login หรือมีคำว่า logout)
            content = self.get_page_content().lower()
            return "logout" in content or "ออกจากระบบ" in content

    def detect_waiting_room(self) -> bool:
        """
        ตรวจจับว่าขณะนี้ติดหน้า Waiting Room / Cloudflare challenge หรือไม่
        """
        if not self.is_open:
            return False
        
        current_url = self.page.url.lower()
        content = self.get_page_content()
        
        # เช็คจากคำค้นหาใน config
        for indicator in config.WAITING_ROOM_INDICATORS:
            if indicator.lower() in content.lower() or indicator.lower() in current_url:
                return True
        return False

    def detect_server_error(self) -> bool:
        """
        ตรวจจับความผิดพลาดของเซิร์ฟเวอร์ (เช่น 522 Connection timed out)
        """
        if not self.is_open:
            return False
        
        content = self.get_page_content()
        
        for indicator in config.SERVER_ERROR_INDICATORS:
            if indicator.lower() in content.lower():
                return True
        return False

    def wait_for_page_ready(self, timeout_seconds: int = 30) -> str:
        """
        เฝ้าสังเกตและรอจนกว่าหน้าเว็บจะพร้อมใช้งาน
        
        Returns:
            'ready': หน้าเว็บพร้อมใช้งาน
            'waiting_room': ยังติดหน้าคิว
            'error': เกิด Server Error หรือ Timeout
        """
        if not self.is_open:
            return "error"
            
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            try:
                # โหลดหน้าใหม่เบาๆ ถ้าเกิด Error 522
                if self.detect_server_error():
                    print("ตรวจพบ Server Error! กำลังลองโหลดใหม่...")
                    self.page.reload()
                    time.sleep(3)
                    continue

                # ถ้ายังอยู่ใน Waiting Room ให้รอ
                if self.detect_waiting_room():
                    time.sleep(config.WAITING_ROOM_POLL_INTERVAL)
                    continue
                
                # ถ้าไม่เจอ waiting room และไม่เจอ error แปลว่าพร้อม
                return "ready"
                
            except Error:
                time.sleep(1)
                
        # หากเกินเวลาและยังติด waiting room
        if self.detect_waiting_room():
            return "waiting_room"
        return "error"

    def take_screenshot(self, name: str) -> str:
        """
        บันทึกภาพหน้าจอขณะเกิดข้อผิดพลาด
        """
        if not self.is_open:
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = os.path.join(config.SCREENSHOT_DIR, filename)
        
        try:
            self.page.screenshot(path=filepath)
            return filepath
        except Error as e:
            print(f"Failed to take screenshot: {e}")
            return ""

    def keep_alive(self):
        """
        เรียกใช้โค้ด JS สั้นๆ เพื่อไม่ให้เซสชันหมดอายุ
        """
        if not self.is_open:
            return
        try:
            # ดึง Title มาตรวจสอบเฉยๆ เพื่อให้หน้าเว็บมีการเคลื่อนไหว
            self.page.evaluate("document.title")
        except Error:
            pass

    def close(self):
        """
        ปิด Browser และหยุด Playwright
        """
        self._is_open = False
        try:
            if self.context:
                self.context.close()
            if self.playwright:
                self.playwright.stop()
        except Error as e:
            print(f"Error during browser close: {e}")
        finally:
            self.context = None
            self.page = None
            self.playwright = None
