"""Application configuration."""

import os
import sys


# Mode: "demo" for local demo server, "production" for reg.msu.ac.th.
MODE = "production"


# URLs
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
    "enroll": f"{PROD_BASE_URL}/enroll.asp",
    "register": f"{PROD_BASE_URL}/enroll.asp",
    "result": f"{PROD_BASE_URL}/enroll.asp",
}


def get_urls():
    return DEMO_URLS if MODE == "demo" else PROD_URLS


# Selectors
SELECTORS_DEMO = {
    "username": "input#username",
    "password": "input#password",
    "login_btn": "button#login-btn",
    "course_code": "input#courseCode",
    "section": "input#section",
    "add_btn": "button#add-btn",
    "confirm_btn": "button#confirm-btn",
    "course_table": "table#course-table",
    "course_table_body": "table#course-table tbody",
    "status_message": "#status-message",
    "status_pending": ".status-pending",
    "status_success": ".status-success",
    "status_full": ".status-full",
    "status_conflict": ".status-conflict",
    "status_not_found": ".status-not_found",
    "register_link": "a#nav-register",
    "logout_btn": "button#logout-btn",
    "dashboard_content": "#dashboard-content",
}

SELECTORS_PROD = {
    "username": "input[name='studentcode']",
    "password": "input[name='studentpassword']",
    "login_btn": "input[name='Submit']",
    "course_code": "input[name='strcoursecode']",
    "section": "input[name='strsec']",
    "add_btn": "input[name='cmdadd']",
    "confirm_btn": "input[name='cmdsave']",
    "course_table": "table",
    "course_table_body": "table tbody",
    "status_message": "font[color='red']",
    "status_pending": "",
    "status_success": "",
    "status_full": "",
    "status_conflict": "",
    "status_not_found": "",
    "register_link": "a[href*='enroll.asp'], a[href*='registration.asp']",
    "logout_btn": "a[href*='logout.asp']",
    "dashboard_content": "td",
}

SELECTORS = SELECTORS_DEMO if MODE == "demo" else SELECTORS_PROD


# Detection text
WAITING_ROOM_INDICATORS = [
    "\u0e02\u0e13\u0e30\u0e19\u0e35\u0e49\u0e04\u0e38\u0e13\u0e2d\u0e22\u0e39\u0e48\u0e43\u0e19\u0e04\u0e34\u0e27\u0e41\u0e25\u0e49\u0e27",
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


# Retry / Timing
RETRY_DELAY_SECONDS = 7
MAX_RETRIES = 5
KEEP_ALIVE_INTERVAL = 60
WAITING_ROOM_POLL_INTERVAL = 3


# Paths
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
    USER_DATA_DIR = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "MSU Registration Helper",
    )
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    USER_DATA_DIR = APP_DIR

BUNDLED_PLAYWRIGHT_BROWSERS_DIR = os.path.join(APP_DIR, "ms-playwright")
BROWSER_PROFILE_DIR = os.path.join(USER_DATA_DIR, "msu_profile")
DB_PATH = os.path.join(USER_DATA_DIR, "msu_helper.db")
SCREENSHOT_DIR = os.path.join(USER_DATA_DIR, "screenshots")
LOG_DIR = os.path.join(USER_DATA_DIR, "logs")

for directory in [USER_DATA_DIR, BROWSER_PROFILE_DIR, SCREENSHOT_DIR, LOG_DIR]:
    os.makedirs(directory, exist_ok=True)


# App info
APP_NAME = "MSU Registration Helper"
APP_VERSION = "1.0.0"
APP_PUBLISHER = "MSU Registration Helper"
APP_ID = "MSURegistrationHelper"
WINDOW_WIDTH = 1040
WINDOW_HEIGHT = 820
