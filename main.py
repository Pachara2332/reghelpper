import sys
import os

# มั่นใจว่าโปรเจกต์ root ถูกค้นพบใน path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from gui.app import MainWindow
from database.db import DatabaseManager
import config

def main():
    # 1. โหลดฐานข้อมูล SQLite
    db = DatabaseManager(config.DB_PATH)
    
    # 2. เริ่มแอป Qt
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setStyle('Fusion')  # ฟิวชันเพื่อให้สไตล์ Dark ทำงานได้ราบรื่นทุกระบบปฏิบัติการ
    
    # 3. โหลด/เปิดหน้าต่างหลัก
    window = MainWindow(db)
    window.show()
    
    # 4. ออกอย่างสวยงาม
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
