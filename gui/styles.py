"""
MSU Registration Helper — Stylesheet
รวบรวมสไตล์ชีต QSS สไตล์ Dark Mode ทันสมัยและหรูหรา
"""

DARK_THEME_QSS = """
/* ---------- Main Window Base ---------- */
QMainWindow {
    background-color: #0d1117;
}

QWidget {
    color: #e6edf3;
    font-family: 'Segoe UI', 'Leelawadee UI', 'Tahoma', sans-serif;
    font-size: 13px;
}

/* ---------- Group Box / Section Containers ---------- */
QGroupBox {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    margin-top: 15px;
    padding-top: 18px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 5px;
    color: #58a6ff;
}

/* ---------- Text Inputs ---------- */
QLineEdit {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 12px;
    color: #e6edf3;
    selection-background-color: #1f6feb;
}

QLineEdit:focus {
    border: 1px solid #58a6ff;
    background-color: #262c36;
}

QLineEdit:disabled {
    background-color: #0d1117;
    color: #8b949e;
    border: 1px solid #21262d;
}

/* ---------- Buttons ---------- */
QPushButton {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 16px;
    color: #c9d1d9;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #8b949e;
}

QPushButton:pressed {
    background-color: #161b22;
}

QPushButton:disabled {
    background-color: #21262d;
    color: #484f58;
    border-color: #21262d;
}

/* Primary Green Button (เช่น ยืนยัน) */
QPushButton#primaryButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2ea043, stop:1 #238636);
    border: 1px solid #3fb950;
    color: #ffffff;
}

QPushButton#primaryButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3fb950, stop:1 #2ea043);
    border-color: #58a6ff;
}

QPushButton#primaryButton:pressed {
    background-color: #238636;
}

QPushButton#primaryButton:disabled {
    background: #102a15;
    color: #2d5a31;
    border-color: #102a15;
}

/* Accent Blue Button (เช่น เปิด Browser, ค้นหา) */
QPushButton#accentButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #388bfd, stop:1 #1f6feb);
    border: 1px solid #58a6ff;
    color: #ffffff;
}

QPushButton#accentButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #58a6ff, stop:1 #388bfd);
    border-color: #c9d1d9;
}

QPushButton#accentButton:pressed {
    background-color: #1f6feb;
}

/* Danger Button (ปุ่ม ลบ หรือ ยกเลิก) */
QPushButton#dangerButton {
    background-color: #da3633;
    border: 1px solid #f85149;
    color: #ffffff;
}

QPushButton#dangerButton:hover {
    background-color: #f85149;
}

QPushButton#dangerButton:pressed {
    background-color: #b62320;
}

/* ---------- Table Widget ---------- */
QTableWidget {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    gridline-color: #30363d;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 6px;
}

QTableWidget::item:alternate {
    background-color: #1f242c;
}

QHeaderView::section {
    background-color: #21262d;
    color: #8b949e;
    padding: 6px;
    border: 1px solid #30363d;
    font-weight: bold;
}

/* ---------- Text Edit (Log Window) ---------- */
QTextEdit {
    background-color: #090c10;
    border: 1px solid #30363d;
    border-radius: 6px;
    font-family: 'Consolas', 'Courier New', monospace;
    padding: 8px;
    color: #c9d1d9;
}

/* ---------- Scrollbars ---------- */
QScrollBar:vertical {
    border: none;
    background: #0d1117;
    width: 8px;
    margin: 0px 0 0px 0;
}

QScrollBar::handle:vertical {
    background: #30363d;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #8b949e;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

/* ---------- Dialogs ---------- */
QDialog {
    background-color: #0d1117;
}

/* ---------- Status indicator styles ---------- */
QLabel#statusBadgePending {
    background-color: #1f2b3d;
    color: #58a6ff;
    border-radius: 10px;
    padding: 2px 8px;
    font-weight: bold;
}

QLabel#statusBadgeSuccess {
    background-color: #132b1a;
    color: #3fb950;
    border-radius: 10px;
    padding: 2px 8px;
    font-weight: bold;
}

QLabel#statusBadgeFull {
    background-color: #331518;
    color: #f85149;
    border-radius: 10px;
    padding: 2px 8px;
    font-weight: bold;
}

QLabel#statusBadgeConflict {
    background-color: #2c210f;
    color: #d29922;
    border-radius: 10px;
    padding: 2px 8px;
    font-weight: bold;
}

QLabel#statusBadgeNotFound {
    background-color: #21262d;
    color: #8b949e;
    border-radius: 10px;
    padding: 2px 8px;
    font-weight: bold;
}
"""
