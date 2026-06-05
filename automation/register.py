"""Registration page automation and scraping."""

import re
import time
from typing import Any

from playwright.sync_api import Error, Page

import config


COURSE_CODE_PATTERN = re.compile(r'^\d{7}(?:-\d+)?$')

INSTRUCTION_KEYWORDS = [
    "รายวิชาที่ต้องการลงทะเบียน",
    "ปีการศึกษา",
    "เลือกหน้าจอบันทึกแบบ",
    "รายวิชาปกติ",
    "รายวิชา thesis",
    "รายวิชา is",
    "คำอธิบาย",
    "ขั้นที่",
    "คำแนะนำ",
    "เมื่อตรวจรหัสรายวิชา",
    "รหัสวิชา",
    "หน่วยกิต",
    "กลุ่ม",
    "จำนวนหน่วยกิตรวม",
    "ตารางสอบ",
    "หมายเหตุ",
    "print friendly",
    "ยืนยันการลงทะเบียน",
    "กลับ",
]


SECTION_KEYS = {
    "course_code": ["รหัสวิชา", "course code", "code"],
    "select": ["เลือก", "select"],
    "course_name": ["ชื่อรายวิชา", "ชื่อวิชา", "course name", "description"],
    "credit": ["หน่วยกิต", "credit"],
    "section": ["กลุ่ม", "หมู่", "section", "sec"],
    "seat": ["รับ/เหลือ", "รับ", "เหลือ", "seat"],
    "time": ["เวลา", "time"],
    "curriculum_structure": ["โครงสร้างหลักสูตร", "curriculum"],
    "status": ["สถานะ", "หมายเหตุ", "note", "status"],
}


def classify_result_message(message: str) -> str:
    lowered = (message or "").lower()
    thai_success = "สำเร็จ"
    thai_done = "เรียบร้อย"
    thai_full = "เต็ม"
    thai_conflict = "ชน"
    thai_not_found = "ไม่พบ"
    thai_pending = "รอยืนยัน"

    if any(word in lowered for word in ["success", thai_success, thai_done]):
        return "success"
    if any(word in lowered for word in ["full", thai_full]):
        return "full"
    if any(word in lowered for word in ["conflict", thai_conflict]):
        return "conflict"
    if any(word in lowered for word in ["invalid", "not found", "not_found", thai_not_found]):
        return "invalid"
    if any(word in lowered for word in ["pending", thai_pending]):
        return "pending"
    return "unknown"


class RegistrationService:
    """Keeps the app mirrored with the real enrollment page."""

    def __init__(self, page: Page):
        self.page = page
        self.selectors = config.SELECTORS
        self.last_dialog_message = ""
        self.page.on("dialog", self._handle_dialog)

    def _handle_dialog(self, dialog):
        self.last_dialog_message = dialog.message
        dialog.accept()

    def navigate_to_register(self) -> bool:
        try:
            urls = config.get_urls()
            target = urls.get("enroll") or urls.get("register")
            current_url = self.page.url.lower()
            if "enroll.asp" in current_url or "registration.asp" in current_url:
                return True

            register_locator = self.page.locator(self.selectors.get("register_link", "a[href*='enroll.asp']")).first
            if register_locator.count() > 0 and register_locator.is_visible():
                register_locator.click()
                self.page.wait_for_load_state("load")
                return True

            self.page.goto(target, wait_until="load")
            return True
        except Error as exc:
            print(f"Error navigating to enrollment page: {exc}")
            return False

    def navigate_to_confirm_enroll(self) -> bool:
        try:
            urls = config.get_urls()
            target = urls.get("confirm_enroll") or f"{config.PROD_BASE_URL}/confirm_enroll.asp"
            current_url = self.page.url.lower()
            if "confirm_enroll.asp" in current_url or "register.html" in current_url:
                return True
            self.page.goto(target, wait_until="load")
            return True
        except Error as exc:
            print(f"Error navigating to confirm enrollment page: {exc}")
            return False

    def sync_existing_pending_courses(self) -> list[dict]:
        self.navigate_to_confirm_enroll()
        return self.refresh_registration_queue()

    def refresh_registration_queue(self) -> list[dict]:
        return self.parse_confirm_enroll_queue()

    def search_course_sections(self, course_code: str) -> list[dict]:
        self.navigate_to_register()
        self.last_dialog_message = ""
        course_code = course_code.strip()
        if not course_code:
            return []

        self._fill_first_available(
            [
                self.selectors.get("course_code", ""),
                "input[name*='course' i]",
                "input[name*='subject' i]",
                "input[type='text']",
            ],
            course_code,
        )
        self._click_first_available(
            [
                self.selectors.get("add_btn", ""),
                "input[value*='ค้น']",
                "input[value*='เพิ่ม']",
                "input[value*='บันทึก']",
                "button:has-text('ค้น')",
                "button:has-text('เพิ่ม')",
                "button:has-text('บันทึก')",
                "input[type='submit']",
            ]
        )
        self._wait_after_action()
        return self.scrape_section_table(course_code)

    def scrape_section_table(self, course_code: str = "") -> list[dict]:
        return self.parse_available_sections(course_code)

    def add_course_by_code_and_section(self, course_code: str, section: str) -> dict[str, Any]:
        """Navigate to enroll.asp, fill course and section, click บันทึก, detect status, and update queue."""
        self.navigate_to_register()

        # 1. Fill course code
        self._fill_first_available(
            [
                self.selectors.get("course_code", ""),
                "input[name*='course' i]",
                "input[name*='subject' i]",
                "input[type='text']",
            ],
            course_code,
        )

        # 2. Fill section/group
        self._fill_first_available(
            [
                self.selectors.get("section", ""),
                "input[name*='sec' i]",
                "input[name*='group' i]",
            ],
            section,
        )

        # 3. Click บันทึก
        self._click_first_available(
            [
                "input[value*='บันทึก']",
                "button:has-text('บันทึก')",
                "input[value*='เพิ่ม']",
                "button:has-text('เพิ่ม')",
                self.selectors.get("confirm_btn", ""),
                self.selectors.get("add_btn", ""),
                "input[type='submit']",
            ]
        )

        self._wait_after_action()

        # 4. Read result message
        result_message = ""
        if self.last_dialog_message:
            result_message = self.last_dialog_message
            self.last_dialog_message = ""
        else:
            try:
                msg_selector = self.selectors.get("status_message")
                if msg_selector:
                    locator = self.page.locator(msg_selector).first
                    if locator.count() > 0 and locator.is_visible():
                        result_message = self._clean_text(locator.inner_text())
            except Exception:
                pass

        status = classify_result_message(result_message)

        # 5. Navigate to confirm_enroll.asp and sync queue
        queue_rows = self.refresh_registration_queue()

        # See if the course now exists in the live queue
        in_queue = any(r.get("course_code") == course_code and r.get("section") == section for r in queue_rows)
        if in_queue and status in {"unknown", "failed"}:
            status = "pending"

        return {
            "status": status,
            "message": result_message or ("Added to queue" if in_queue else "Not in queue"),
            "queue": queue_rows
        }

    @staticmethod
    def is_valid_course_code(text: str) -> bool:
        """Return True if text looks like a valid MSU course code (7 digits, optionally with -N suffix)."""
        cleaned = re.sub(r'\s+', '', (text or '').strip())
        return bool(COURSE_CODE_PATTERN.match(cleaned))

    @staticmethod
    def is_instruction_row(row_text: str) -> bool:
        """Return True if the row text contains instruction/header text that is not a course."""
        lowered = (row_text or '').lower()
        return any(keyword in lowered for keyword in INSTRUCTION_KEYWORDS)

    def parse_pending_courses(self) -> list[dict]:
        """Parse only real pending course rows from the enrollment page (non-selectable, valid course code)."""
        rows = self._scrape_tables()
        result = []
        for row in rows:
            if row.get('selectable'):
                continue
            if not self.is_valid_course_code(row.get('course_code', '')):
                continue
            row_text = ' '.join(str(v) for v in row.values())
            if self.is_instruction_row(row_text):
                continue
            row['status'] = 'pending'
            result.append(row)
        return result

    def parse_available_sections(self, course_code: str = '') -> list[dict]:
        """Parse only real available section rows (selectable, valid course code)."""
        rows = self._scrape_tables()
        result = []
        for row in rows:
            if not row.get('selectable'):
                continue
            if not self.is_valid_course_code(row.get('course_code', '')):
                continue
            # Filter out top input form (which doesn't have time or seat details)
            if not row.get('time') and not row.get('seat'):
                continue
            row_text = ' '.join(str(v) for v in row.values())
            if self.is_instruction_row(row_text):
                continue
            if course_code and course_code not in row.get('course_code', ''):
                continue
            row['status'] = 'available'
            result.append(row)
        return result

    def parse_confirm_enroll_queue(self) -> list[dict]:
        """Scrape the registration queue from confirm_enroll.asp."""
        self.navigate_to_confirm_enroll()

        if config.MODE == "demo":
            return self.parse_pending_courses()

        tables = self.page.locator("table")
        results = []
        for t_idx in range(tables.count()):
            table = tables.nth(t_idx)
            trs = table.locator("tr")
            for r_idx in range(trs.count()):
                tr = trs.nth(r_idx)
                row_text = tr.inner_text()
                # Clean up whitespace
                clean_text = ' '.join(row_text.split())

                # Check if this row contains a valid 7-digit course code
                match = re.search(r'\b(\d{7})\b', clean_text)
                if not match:
                    continue

                course_code = match.group(1)

                # Use regex to find credits
                credit_match = re.search(r'(?:หน่วยกิต|credit)\s*:?\s*(\d+)', clean_text, re.IGNORECASE)
                credit = credit_match.group(1) if credit_match else ""

                # Use regex to find group/section
                sec_match = re.search(r'(?:กลุ่ม|หมู่เรียน|หมู่|sec|section|group)\s*:?\s*(\d+)', clean_text, re.IGNORECASE)
                section = sec_match.group(1) if sec_match else ""

                # Parse the course name (text between code and next label)
                name_match = re.search(rf'{course_code}\s*(.*?)\s*(?:หน่วยกิต|credit|กลุ่ม|หมู่|sec)', clean_text, re.IGNORECASE)
                course_name = name_match.group(1).strip() if name_match else ""

                if self.is_instruction_row(clean_text):
                    continue

                # Avoid duplicates
                if any(r["course_code"] == course_code and r["section"] == section for r in results):
                    continue

                results.append({
                    "course_code": course_code,
                    "course_name": course_name,
                    "credit": credit,
                    "section": section,
                    "status": "pending",
                    "selectable": False
                })
        return results

    def select_section(self, course_code: str, section: str) -> list[dict]:
        self.navigate_to_register()
        row = self._find_page_row(course_code, section)
        if row is None:
            raise RuntimeError(f"Section not found on page: {course_code} section {section}")

        checkbox = row.locator("input[type='checkbox'], input[type='radio']").first
        if checkbox.count() > 0:
            checkbox.check()
        else:
            clickable = row.locator("a, button, input[type='button'], input[type='submit']").first
            if clickable.count() > 0:
                clickable.click()

        self._fill_section_if_needed(section)
        self._click_first_available(
            [
                "input[value*='บันทึก']",
                "button:has-text('บันทึก')",
                "input[value*='เพิ่ม']",
                "button:has-text('เพิ่ม')",
                self.selectors.get("confirm_btn", ""),
                self.selectors.get("add_btn", ""),
                "input[type='submit']",
            ]
        )
        self._wait_after_action()
        return self.refresh_registration_queue()

    def confirm_registration(self) -> bool:
        self.navigate_to_confirm_enroll()
        try:
            clicked = self._click_first_available(
                [
                    self.selectors.get("confirm_btn", ""),
                    "input[value*='ยืนยัน']",
                    "button:has-text('ยืนยัน')",
                    "input[value*='บันทึก']",
                    "button:has-text('บันทึก')",
                ]
            )
            if clicked:
                self._wait_after_action()
            return clicked
        except Error as exc:
            print(f"Error confirming registration: {exc}")
            return False

    # Compatibility with older call sites.
    def retry_add_course(self, course_code: str, section: str, max_retries: int | None = None, delay: int | None = None) -> dict[str, Any]:
        rows = self.select_section(course_code, section)
        match = next((row for row in rows if row.get("course_code") == course_code and row.get("section") == section), {})
        return {
            "status": "pending",
            "message": "Selected from real enrollment page.",
            "name": match.get("course_name", ""),
        }

    def drop_course(self, course_code: str, section: str) -> dict[str, Any]:
        return {
            "status": "skipped",
            "message": "Drop is not implemented for the mirrored enrollment flow.",
            "name": "",
        }

    def read_results(self) -> list[dict[str, str]]:
        return self.refresh_registration_queue()

    def _scrape_tables(self) -> list[dict]:
        tables = self.page.locator("table")
        result: list[dict] = []
        for table_index in range(tables.count()):
            table = tables.nth(table_index)
            headers = self._table_headers(table)
            trs = table.locator("tr")
            for row_index in range(trs.count()):
                tr = trs.nth(row_index)
                cells = tr.locator("td")
                if cells.count() < 2:
                    continue
                row = self._parse_row(tr, headers)
                if not row.get("course_code") and not row.get("course_name"):
                    continue
                full_row_text = ' '.join(str(v) for v in row.values())
                if self.is_instruction_row(full_row_text):
                    continue
                row["source_table_index"] = table_index
                row["source_row_index"] = row_index
                row.setdefault("status", "จากเว็บจริง / From website")
                result.append(row)
        return result

    def _table_headers(self, table) -> list[str]:
        headers = []
        ths = table.locator("tr").first.locator("th,td")
        for i in range(ths.count()):
            headers.append(self._clean_text(ths.nth(i).inner_text()))
        return headers

    def _parse_row(self, tr, headers: list[str]) -> dict:
        cells = tr.locator("td")
        values = [self._clean_text(cells.nth(i).inner_text()) for i in range(cells.count())]
        has_select_header = any(self._key_for_header(header) == "select" for header in headers)
        selectable = has_select_header
        row = {
            "course_code": "",
            "selectable": selectable,
            "course_name": "",
            "credit": "",
            "section": "",
            "seat": "",
            "time": "",
            "curriculum_structure": "",
            "status": "",
        }

        for idx, value in enumerate(values):
            key = self._key_for_header(headers[idx] if idx < len(headers) else "")
            if key and key != "select":
                row[key] = value

        if not row["course_code"]:
            for value in values:
                match = re.search(r"\b\d{6,8}\b", value)
                if match:
                    row["course_code"] = match.group(0)
                    break

        # Fallback for pages with weak/no headers.
        non_empty = [v for v in values if v]
        if non_empty:
            row["course_code"] = row["course_code"] or non_empty[0]
        if len(non_empty) >= 2 and not row["course_name"]:
            row["course_name"] = non_empty[1]
        if len(non_empty) >= 3 and not row["credit"]:
            row["credit"] = non_empty[2]
        if len(non_empty) >= 4 and not row["section"]:
            row["section"] = non_empty[3]
        if len(non_empty) >= 5 and not row["seat"]:
            row["seat"] = non_empty[4]
        if len(non_empty) >= 6 and not row["time"]:
            row["time"] = non_empty[5]
        if len(non_empty) >= 7 and not row["curriculum_structure"]:
            row["curriculum_structure"] = non_empty[6]
        if len(non_empty) >= 8 and not row["status"]:
            row["status"] = non_empty[7]

        return row

    def _find_page_row(self, course_code: str, section: str):
        rows = self.page.locator("table tr")
        for index in range(rows.count()):
            row = rows.nth(index)
            text = self._clean_text(row.inner_text())
            if course_code in text and re.search(rf"(^|\s){re.escape(section)}(\s|$)", text):
                return row
        return None

    def _fill_section_if_needed(self, section: str):
        try:
            locator = self.page.locator(self.selectors.get("section", "")).first
            if locator.count() > 0 and locator.is_visible():
                locator.fill(section)
        except Error:
            pass

    def _fill_first_available(self, selectors: list[str], value: str) -> bool:
        for selector in [s for s in selectors if s]:
            try:
                locator = self.page.locator(selector).first
                if locator.count() > 0 and locator.is_visible():
                    locator.fill("")
                    locator.fill(value)
                    return True
            except Error:
                pass
        raise RuntimeError("Course code input was not found on the enrollment page.")

    def _click_first_available(self, selectors: list[str]) -> bool:
        for selector in [s for s in selectors if s]:
            try:
                locator = self.page.locator(selector).first
                if locator.count() > 0 and locator.is_visible() and locator.is_enabled():
                    locator.click()
                    return True
            except Error:
                pass
        return False

    def _wait_after_action(self):
        try:
            self.page.wait_for_load_state("load", timeout=8000)
        except Error:
            pass
        time.sleep(1.0)

    def _key_for_header(self, header: str) -> str:
        normalized = header.lower().replace("\n", " ").strip()
        for key, candidates in SECTION_KEYS.items():
            if any(candidate in normalized for candidate in candidates):
                return key
        return ""

    @staticmethod
    def _clean_text(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()
