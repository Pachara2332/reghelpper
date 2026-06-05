"""
MSU Registration Helper — Configuration
ตั้งค่า URLs, selectors, และ app settings ทั้งหมดไว้ที่นี่
"""

import os

# ─── Mode ────────────────────────────────────────────────────
# "demo" = ใช้ demo server (localhost)
# "production" = ใช้เว็บจริง reg.msu.ac.th
MODE = "production"  # เปลี่ยนเป็น "demo" เพื่อทดสอบกับ demo server

# ─── URLs ────────────────────────────────────────────────────
DEMO_BASE_URL = "http://localhost:8899"
DEMO_URLS = {
    "login": f"{DEMO_BASE_URL}/index.html",
    "dashboard": f"{DEMO_BASE_URL}/dashboard.html",
    "register": f"{DEMO_BASE_URL}/register.html",
    "result": f"{DEMO_BASE_URL}/result.html",
}

PROD_BASE_URL = "https://reg.msu.ac.th/registrar"
PROD_URLS = {
    "login": f"{PROD_BASE_URL}/login.asp",
    "dashboard": f"{PROD_BASE_URL}/student.asp",
    "register": f"{PROD_BASE_URL}/registration.asp",
    "result": f"{PROD_BASE_URL}/registration.asp",
}

def get_urls():
    """Return URL dict based on current MODE."""
    return DEMO_URLS if MODE == "demo" else PROD_URLS

# ─── Selectors ───────────────────────────────────────────────
SELECTORS_DEMO = {
    # Login page
    "username": "input#username",
    "password": "input#password",
    "login_btn": "button#login-btn",

    # Registration page
    "course_code": "input#courseCode",
    "section": "input#section",
    "add_btn": "button#add-btn",
    "confirm_btn": "button#confirm-btn",
    "course_table": "table#course-table",
    "course_table_body": "table#course-table tbody",
    "status_message": "#status-message",

    # Status classes
    "status_pending": ".status-pending",
    "status_success": ".status-success",
    "status_full": ".status-full",
    "status_conflict": ".status-conflict",
    "status_not_found": ".status-not_found",

    # Navigation
    "register_link": "a#nav-register",
    "logout_btn": "button#logout-btn",

    # Dashboard
    "dashboard_content": "#dashboard-content",
}

SELECTORS_PROD = {
    # Login page
    "username": "input[name='studentcode']",
    "password": "input[name='studentpassword']",
    "login_btn": "input[name='Submit']",  # หรือ input[type='submit']

    # Registration page (Registrar ASP)
    "course_code": "input[name='strcoursecode']",
    "section": "input[name='strsec']",
    "add_btn": "input[name='cmdadd']",
    "confirm_btn": "input[name='cmdsave']",
    "course_table": "table",
    "course_table_body": "table tbody",
    "status_message": "font[color='red']", # ปกติจะแสดงข้อความเตือนเป็นสีแดง

    # Status classes (เว็บจริงจะใช้ข้อความข้างในเป็นหลัก)
    "status_pending": "",
    "status_success": "",
    "status_full": "",
    "status_conflict": "",
    "status_not_found": "",

    # Navigation
    "register_link": "a[href*='registration.asp']",
    "logout_btn": "a[href*='logout.asp']",

    # Dashboard
    "dashboard_content": "td",
}

# กำหนด Selectors ตามโหมดที่เลือก
SELECTORS = SELECTORS_DEMO if MODE == "demo" else SELECTORS_PROD


# ─── Waiting Room / Error Detection ─────────────────────────
WAITING_ROOM_INDICATORS = [
    "ขณะนี้คุณอยู่ในคิวแล้ว",
    "Checking if the site connection is secure",
    "Please wait",
    "Just a moment",
    "cf-waiting-room",
    "challenges.cloudflare.com",
]

SERVER_ERROR_INDICATORS = [
    "522",
    "Connection timed out",
    "502 Bad Gateway",
    "503 Service Unavailable",
    "504 Gateway Timeout",
    "ERR_CONNECTION_TIMED_OUT",
]

# ─── Retry / Timing ─────────────────────────────────────────
RETRY_DELAY_SECONDS = 7          # delay ระหว่าง retry (ไม่รัว)
MAX_RETRIES = 5                  # จำนวน retry สูงสุดต่อวิชา
KEEP_ALIVE_INTERVAL = 60         # วินาที ระหว่าง keep-alive check
WAITING_ROOM_POLL_INTERVAL = 3   # วินาที ระหว่าง poll waiting room

# ─── Paths ───────────────────────────────────────────────────
import sys
if getattr(sys, 'frozen', False):
    # รันจากไฟล์ .exe ที่ถูกคอมไพล์ (PyInstaller)
    APP_DIR = os.path.dirname(sys.executable)
else:
    # รันจากไฟล์ .py ปกติ
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

BROWSER_PROFILE_DIR = os.path.join(APP_DIR, "msu_profile")
DB_PATH = os.path.join(APP_DIR, "msu_helper.db")
SCREENSHOT_DIR = os.path.join(APP_DIR, "screenshots")
LOG_DIR = os.path.join(APP_DIR, "logs")

# Create directories if needed
for d in [SCREENSHOT_DIR, LOG_DIR]:
    os.makedirs(d, exist_ok=True)

# ─── App Info ────────────────────────────────────────────────
APP_NAME = "MSU Registration Helper"
APP_VERSION = "1.0.0"
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 900

