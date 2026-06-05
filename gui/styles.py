"""Application stylesheet."""

DARK_THEME_QSS = """
QMainWindow {
    background-color: #0f141b;
}

QWidget {
    color: #eef3f8;
    font-family: 'Leelawadee UI', 'Tahoma', 'Segoe UI', sans-serif;
    font-size: 14px;
}

QGroupBox {
    background-color: #171d25;
    border: 1px solid #2f3946;
    border-radius: 8px;
    margin-top: 18px;
    padding: 16px 12px 12px 12px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 8px;
    color: #7cc7ff;
    background-color: #0f141b;
}

QLabel#hintText {
    color: #9aa7b5;
    font-size: 12px;
}

QLineEdit, QComboBox, QSpinBox {
    background-color: #222a34;
    border: 1px solid #364252;
    border-radius: 6px;
    min-height: 22px;
    padding: 7px 10px;
    color: #f5f8fb;
    selection-background-color: #2d7dd2;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #7cc7ff;
    background-color: #27313d;
}

QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
    background-color: #151a21;
    color: #7a8794;
    border: 1px solid #27313d;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QPushButton {
    background-color: #24303c;
    border: 1px solid #3a4655;
    border-radius: 6px;
    min-height: 22px;
    padding: 7px 14px;
    color: #eef3f8;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #2d3948;
    border-color: #6f8195;
}

QPushButton:pressed {
    background-color: #1d2630;
}

QPushButton:disabled {
    background-color: #1a2028;
    color: #596574;
    border-color: #242b34;
}

QPushButton#primaryButton {
    background-color: #248a3d;
    border: 1px solid #38b558;
    color: #ffffff;
}

QPushButton#primaryButton:hover {
    background-color: #2fa64a;
}

QPushButton#primaryButton:pressed {
    background-color: #1d7132;
}

QPushButton#primaryButton:disabled {
    background-color: #17301d;
    color: #56825f;
    border-color: #1f3b25;
}

QPushButton#accentButton {
    background-color: #2374d8;
    border: 1px solid #58a9ff;
    color: #ffffff;
}

QPushButton#accentButton:hover {
    background-color: #348bf0;
}

QPushButton#accentButton:pressed {
    background-color: #1b5eb3;
}

QPushButton#dangerButton {
    background-color: #8f2f2f;
    border: 1px solid #d95555;
    color: #ffffff;
}

QPushButton#dangerButton:hover {
    background-color: #b53f3f;
}

QPushButton#dangerButton:pressed {
    background-color: #742727;
}

QTableWidget {
    background-color: #121821;
    border: 1px solid #2f3946;
    border-radius: 6px;
    gridline-color: #28313d;
    selection-background-color: #264f78;
    selection-color: #ffffff;
    alternate-background-color: #171f2a;
}

QTableWidget::item {
    padding: 7px;
}

QHeaderView::section {
    background-color: #222a34;
    color: #b8c3cf;
    padding: 8px;
    border: 1px solid #303946;
    font-weight: bold;
}

QTextEdit {
    background-color: #0b1016;
    border: 1px solid #2f3946;
    border-radius: 6px;
    font-family: 'Leelawadee UI', 'Tahoma', 'Segoe UI', sans-serif;
    font-size: 12px;
    padding: 8px;
    color: #d9e2ec;
}

QScrollBar:vertical {
    border: none;
    background: #10161d;
    width: 8px;
    margin: 0px 0 0px 0;
}

QScrollBar::handle:vertical {
    background: #3a4655;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #738397;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QDialog {
    background-color: #0f141b;
}

QLabel#statusBadgePending {
    background-color: #17334f;
    color: #86c8ff;
    border-radius: 9px;
    padding: 3px 8px;
    font-weight: bold;
}

QLabel#statusBadgeSuccess {
    background-color: #17351f;
    color: #6fdd87;
    border-radius: 9px;
    padding: 3px 8px;
    font-weight: bold;
}

QLabel#statusBadgeFull {
    background-color: #451d20;
    color: #ff8585;
    border-radius: 9px;
    padding: 3px 8px;
    font-weight: bold;
}

QLabel#statusBadgeConflict {
    background-color: #3b2b12;
    color: #f2c35b;
    border-radius: 9px;
    padding: 3px 8px;
    font-weight: bold;
}

QLabel#statusBadgeNotFound {
    background-color: #252d37;
    color: #b4beca;
    border-radius: 9px;
    padding: 3px 8px;
    font-weight: bold;
}
"""
