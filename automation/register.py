"""
MSU Registration Helper — Registration Service
บริการทำธุรกรรมลงทะเบียนบนเว็บเพจผ่าน Playwright
"""

import time
from typing import Dict, List, Any, Optional
from playwright.sync_api import Page, Error

import config

class RegistrationService:
    """
    คุมหน้าเว็บการลงทะเบียนเรียน: กรอกข้อมูลวิชา, เพิ่มวิชา, ยืนยันผล
    """

    def __init__(self, page: Page):
        self.page = page
        self.selectors = config.SELECTORS
        self.last_dialog_message = ""
        
        # เชื่อมต่อ Event Listener สำหรับดักจับกล่องข้อความ Alert / Confirm
        self.page.on("dialog", self._handle_dialog)

    def _handle_dialog(self, dialog):
        """จัดการกับกล่องข้อความระบบ (Alert/Confirm) อัตโนมัติ"""
        self.last_dialog_message = dialog.message
        print(f"ตรวจพบ Dialog: {dialog.message}")
        dialog.accept()

    def navigate_to_register(self) -> bool:
        """ไปยังหน้าลงทะเบียน"""
        try:
            urls = config.get_urls()
            
            # ถ้าอยู่ในหน้า dashboard แล้ว ให้คลิกลิงก์เมนูลงทะเบียนเรียน หรือพิมพ์ URL ตรงๆ
            if config.MODE == "demo":
                self.page.goto(urls["register"], wait_until="load")
                return True
            else:
                # สำหรับเว็บจริง เผื่อต้องคลิกจากเมนู sidebar หรือนำทางตรง
                current_url = self.page.url.lower()
                if "registration.asp" in current_url:
                    return True
                
                # ลองค้นหาลิงก์ลงทะเบียนในหน้าเว็บ
                register_locator = self.page.locator(self.selectors["register_link"])
                if register_locator.is_visible():
                    register_locator.click()
                    self.page.wait_for_load_state("load")
                    return True
                else:
                    self.page.goto(urls["register"], wait_until="load")
                    return True
        except Error as e:
            print(f"Error navigating to register page: {e}")
            return False

    def add_course(self, course_code: str, section: str) -> Dict[str, Any]:
        """
        กรอกข้อมูลรายวิชาและกดเพิ่มรายวิชาในหน้าเว็บ
        
        Returns:
            dict: {
                'status': 'pending'|'success'|'full'|'conflict'|'not_found'|'unknown',
                'message': ข้อความจากระบบ,
                'name': ชื่อวิชา (ถ้าอ่านได้)
            }
        """
        result = {
            "status": "unknown",
            "message": "ไม่ทราบผลการดำเนินการ",
            "name": ""
        }
        self.last_dialog_message = "" # รีเซ็ตค่า Dialog ก่อนทำรายการ

        try:
            # 1. รอจนกว่าช่องกรอกรหัสวิชาจะพร้อมใช้งาน
            self.page.wait_for_selector(self.selectors["course_code"], timeout=10000)
            
            # 2. ล้างข้อมูลเก่าและกรอกข้อมูลใหม่
            self.page.fill(self.selectors["course_code"], "")
            self.page.fill(self.selectors["course_code"], course_code)
            
            self.page.fill(self.selectors["section"], "")
            self.page.fill(self.selectors["section"], section)
            
            # 3. กดปุ่มเพิ่มรายวิชา
            self.page.click(self.selectors["add_btn"])
            
            # 4. รอให้ข้อความแสดงสถานะแสดงขึ้นมาหรืออัปเดตตาราง
            time.sleep(1.5) # รอหน้าเว็บประมวลผล
            
            # 5. วิเคราะห์สถานะ (สำหรับเว็บจริง คีย์เวิร์ดมักจะแสดงบน Alert Dialog หรือบนหน้าเว็บ)
            combined_text = ""
            
            # เช็คจาก Alert dialog เป็นอันดับแรก
            if self.last_dialog_message:
                combined_text = self.last_dialog_message
                result["message"] = self.last_dialog_message
            else:
                # เช็คจาก Font สีแดง หรือพื้นที่แสดงผลลัพธ์
                status_msg_locator = self.page.locator(self.selectors["status_message"])
                if status_msg_locator.count() > 0 and status_msg_locator.first.is_visible():
                    combined_text = status_msg_locator.first.inner_text().strip()
                    result["message"] = combined_text
                else:
                    # ค้นหาข้อความเตือนทั่วไปจากเนื้อหาในหน้าเว็บ
                    combined_text = self.page.inner_text("body")
            
            # แปลงคีย์เวิร์ดสถานะ
            if combined_text:
                if any(x in combined_text for x in ["สำเร็จ", "เรียบร้อย", "pending", "success"]):
                    result["status"] = "pending"
                elif any(x in combined_text for x in ["เต็ม", "เกินจำนวนรับ", "full"]):
                    result["status"] = "full"
                    result["message"] = "ที่นั่งเต็ม"
                elif any(x in combined_text for x in ["ชน", "conflict"]):
                    result["status"] = "conflict"
                    result["message"] = "เวลาเรียนหรือเวลาสอบชนกัน"
                elif any(x in combined_text for x in ["ไม่พบ", "ไม่มีรหัสวิชา", "not found", "not_found"]):
                    result["status"] = "not_found"
                    result["message"] = "ไม่พบรหัสวิชานี้ในระบบ"

            # 6. พยายามดึงชื่อวิชาจากตารางในหน้าเว็บ
            rows = self.page.locator(f"{self.selectors['course_table_body']} tr")
            row_count = rows.count()
            
            if row_count > 0:
                for i in range(row_count):
                    row = rows.nth(i)
                    cells = row.locator("td")
                    cell_count = cells.count()
                    
                    if cell_count >= 3:
                        # ลองแมตช์รหัสวิชาและเซค (สำหรับทั้งแบบ Demo และแบบเว็บจริงของมหาลัย)
                        td_code = cells.nth(0).inner_text().strip()
                        
                        # ในเว็บจริง บางครั้งวิชาจะอยู่ในรูปแบบ '0041001' หรือ '0041001-58'
                        if course_code in td_code:
                            # สแกนหา Sec ในคอลัมน์ต่างๆ
                            for c_idx in range(1, cell_count):
                                cell_val = cells.nth(c_idx).inner_text().strip()
                                if cell_val == section:
                                    # คาดว่าชื่อวิชาจะอยู่ก่อนหน้า Sec
                                    result["name"] = cells.nth(c_idx - 1).inner_text().strip()
                                    if result["status"] == "unknown":
                                        result["status"] = "pending" # ถ้ามีในตารางแสดงว่าสำเร็จขั้นแรก
                                    break
                            
                            # ถ้าเป็นแบบ Demo
                            if cell_count >= 4:
                                td_sec = cells.nth(2).inner_text().strip()
                                if td_sec == section:
                                    result["name"] = cells.nth(1).inner_text().strip()
                                    td_status = cells.nth(3)
                                    badge_locator = td_status.locator("span")
                                    if badge_locator.count() > 0:
                                        badge_class = badge_locator.get_attribute("class") or ""
                                        if "status-pending" in badge_class:
                                            result["status"] = "pending"
                                        elif "status-full" in badge_class:
                                            result["status"] = "full"
                                        elif "status-conflict" in badge_class:
                                            result["status"] = "conflict"
                                        elif "status-not_found" in badge_class:
                                            result["status"] = "not_found"
                                        elif "status-success" in badge_class:
                                            result["status"] = "success"
                                    break
            
            # ถ้ายังมีสถานะ unknown แต่รันไม่ล้มเหลว และไม่มีข้อผิดพลาดแจ้ง
            if result["status"] == "unknown" and not self.last_dialog_message:
                # สรุปว่าเป็นสำเร็จขั้นแรกไว้ก่อน
                result["status"] = "pending"
                result["message"] = "เพิ่มวิชาแล้ว (กรุณาตรวจสอบหน้าเว็บบราวเซอร์)"
            
        except Error as e:
            result["status"] = "unknown"
            result["message"] = f"เกิดข้อผิดพลาดในการสั่งการ Browser: {str(e)}"
            
        return result

    def get_table_courses(self) -> List[Dict[str, str]]:
        """
        ดึงรายการวิชาทั้งหมดในตารางของหน้าเว็บ ณ ขณะนั้น
        """
        courses = []
        try:
            rows = self.page.locator(f"{self.selectors['course_table_body']} tr")
            count = rows.count()
            for i in range(count):
                row = rows.nth(i)
                cells = row.locator("td")
                if cells.count() >= 4:
                    courses.append({
                        "course_code": cells.nth(0).inner_text().strip(),
                        "name": cells.nth(1).inner_text().strip(),
                        "section": cells.nth(2).inner_text().strip(),
                        "status": cells.nth(3).inner_text().strip()
                    })
        except Error as e:
            print(f"Error reading course table: {e}")
        return courses

    def confirm_registration(self) -> bool:
        """
        กดปุ่มยืนยันการลงทะเบียนในหน้าเว็บ
        """
        try:
            confirm_btn = self.page.locator(self.selectors["confirm_btn"])
            if confirm_btn.is_visible() and confirm_btn.is_enabled():
                confirm_btn.click()
                self.page.wait_for_load_state("load")
                return True
            return False
        except Error as e:
            print(f"Error confirming registration: {e}")
            return False

    def read_results(self) -> List[Dict[str, str]]:
        """
        อ่านข้อมูลตารางสรุปผลหลังยืนยันการลงทะเบียน (จากหน้า result.html)
        """
        results = []
        try:
            # ค้นหาตารางผลลัพธ์
            rows = self.page.locator("table tbody tr")
            count = rows.count()
            for i in range(count):
                row = rows.nth(i)
                cells = row.locator("td")
                if cells.count() >= 4:
                    results.append({
                        "course_code": cells.nth(0).inner_text().strip(),
                        "name": cells.nth(1).inner_text().strip(),
                        "section": cells.nth(2).inner_text().strip(),
                        "result": cells.nth(3).inner_text().strip()
                    })
        except Error as e:
            print(f"Error reading result page: {e}")
        return results

    def retry_add_course(self, course_code: str, section: str, max_retries: Optional[int] = None, delay: Optional[int] = None) -> Dict[str, Any]:
        """
        พยายามกดเพิ่มวิชาใหม่กรณีระบบเต็มหรือขัดข้อง โดยมี delay ตามที่ระบุ
        """
        retries = max_retries or config.MAX_RETRIES
        wait_time = delay or config.RETRY_DELAY_SECONDS
        
        last_result = {}
        for attempt in range(1, retries + 1):
            print(f"พยายามเพิ่มวิชา {course_code} Sec {section} ครั้งที่ {attempt}/{retries}")
            last_result = self.add_course(course_code, section)
            
            if last_result["status"] in ["pending", "success"]:
                # ถ้าสำเร็จหรือรอยืนยัน ให้พอเลย
                break
                
            if attempt < retries:
                time.sleep(wait_time)
                
        return last_result

    def drop_course(self, course_code: str, section: str) -> Dict[str, Any]:
        """
        ลดรายวิชา/ลบรายวิชาออกจากตารางลงทะเบียนเรียน
        """
        result = {
            "status": "unknown",
            "message": "ไม่พบรายวิชาที่จะลด",
            "name": ""
        }
        self.last_dialog_message = ""
        
        try:
            # 1. นำทางและสแกนแถวตาราง
            rows = self.page.locator(f"{self.selectors['course_table_body']} tr")
            row_count = rows.count()
            
            found = False
            for i in range(row_count):
                row = rows.nth(i)
                cells = row.locator("td")
                cell_count = cells.count()
                
                if cell_count >= 3:
                    td_code = cells.nth(0).inner_text().strip()
                    # ตรวจสอบรหัสวิชา
                    if course_code in td_code:
                        # หาว่า Sec ตรงกันในคอลัมน์ใด
                        sec_found = False
                        for c_idx in range(1, cell_count):
                            cell_val = cells.nth(c_idx).inner_text().strip()
                            if cell_val == section:
                                sec_found = True
                                result["name"] = cells.nth(c_idx - 1).inner_text().strip()
                                break
                        
                        # หรือสำหรับ Demo mode
                        if not sec_found and cell_count >= 4:
                            td_sec = cells.nth(2).inner_text().strip()
                            if td_sec == section:
                                sec_found = True
                                result["name"] = cells.nth(1).inner_text().strip()
                                
                        if sec_found:
                            found = True
                            # พบแถวแล้ว! ให้ทำการคลิกปุ่มลบในแถวนั้น หรือติ๊ก checkbox ลบ
                            # 2.1 ลองกดปุ่มที่มีข้อความว่า "ลบ" หรือ คลาสปุ่มสีแดง
                            del_btn = row.locator("button:has-text('ลบ'), input[type='button'][value='ลบ'], a:has-text('ลบ')")
                            if del_btn.count() > 0 and del_btn.first.is_visible():
                                del_btn.first.click()
                                time.sleep(1.5)
                            else:
                                # 2.2 หากเป็นเว็บจริง อาจจะใช้ Checkbox และกดยืนยันลบด้านล่าง
                                checkbox = row.locator("input[type='checkbox']")
                                if checkbox.count() > 0:
                                    checkbox.first.check()
                                    time.sleep(0.5)
                                    # คลิกปุ่มลบด้านนอกตาราง (เช่น cmddel)
                                    del_outer = self.page.locator("input[name='cmddel'], input[value*='ลบ'], button:has-text('ลบ')")
                                    if del_outer.count() > 0 and del_outer.first.is_visible():
                                        del_outer.first.click()
                                        time.sleep(1.5)
                            
                            # 3. วิเคราะห์ผลจากการทำรายการ
                            combined_text = ""
                            if self.last_dialog_message:
                                combined_text = self.last_dialog_message
                                result["message"] = self.last_dialog_message
                            else:
                                status_msg_locator = self.page.locator(self.selectors["status_message"])
                                if status_msg_locator.count() > 0 and status_msg_locator.first.is_visible():
                                    combined_text = status_msg_locator.first.inner_text().strip()
                                    result["message"] = combined_text
                                else:
                                    combined_text = self.page.inner_text("body")
                                    
                            result["status"] = "pending" # บันทึกเป็นสำเร็จรอเซฟไว้ก่อน
                            result["message"] = "ลดรายวิชาสำเร็จ (รอยืนยัน)"
                            break
                            
            if not found:
                result["status"] = "not_found"
                result["message"] = f"ไม่พบวิชา {course_code} Sec {section} ในตารางที่จะลบ"
                
        except Error as e:
            result["status"] = "unknown"
            result["message"] = f"เกิดข้อผิดพลาดขณะลบวิชา: {str(e)}"
            
        return result

