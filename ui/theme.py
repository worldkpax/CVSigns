from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


def app_stylesheet(color_scheme: Qt.ColorScheme | None = None) -> str:
    is_dark = color_scheme != Qt.ColorScheme.Light
    if is_dark:
        window_bg = ("#0c0c0d", "#121213", "#1a1a1c")
        text_primary = "#f4f4f5"
        text_secondary = "rgba(244, 244, 245, 0.66)"
        border = "rgba(255, 255, 255, 0.14)"
        field_bg = "rgba(255, 255, 255, 0.06)"
        field_focus = "rgba(255, 255, 255, 0.10)"
        surface = "#171719"
        scroll_handle = "rgba(255, 255, 255, 0.22)"
        slider_fill = "rgba(210, 210, 214, 0.90)"
        slider_border = "rgba(255, 255, 255, 0.24)"
    else:
        window_bg = ("#f7f7f8", "#f2f2f3", "#ededee")
        text_primary = "#111113"
        text_secondary = "rgba(17, 17, 19, 0.58)"
        border = "rgba(17, 17, 19, 0.10)"
        field_bg = "rgba(17, 17, 19, 0.04)"
        field_focus = "rgba(17, 17, 19, 0.08)"
        surface = "#ffffff"
        scroll_handle = "rgba(17, 17, 19, 0.20)"
        slider_fill = "rgba(90, 90, 94, 0.72)"
        slider_border = "rgba(17, 17, 19, 0.12)"

    return f"""
    QMainWindow {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:1,
            stop:0 {window_bg[0]},
            stop:0.5 {window_bg[1]},
            stop:1 {window_bg[2]}
        );
    }}
    QWidget#appRoot {{
        background: transparent;
        color: {text_primary};
        font-family: "SF Pro Display", "Segoe UI", sans-serif;
        font-size: 13px;
    }}
    QWidget#controlPanelRoot {{
        background: rgba(0, 0, 0, 0.025);
        border-radius: 34px;
    }}
    QMenuBar {{
        background: transparent;
        color: {text_primary};
        border: none;
        padding: 4px 10px;
    }}
    QMenuBar::item {{
        background: transparent;
        border-radius: 10px;
        padding: 8px 12px;
    }}
    QMenuBar::item:selected {{
        background: rgba(255, 255, 255, 0.12);
    }}
    QStatusBar {{
        background: {field_bg};
        color: {text_primary};
        border-top: 1px solid {border};
    }}
    QStatusBar::item {{
        border: none;
    }}
    QSplitter::handle {{
        background: transparent;
        width: 12px;
    }}
    QScrollArea {{
        background: transparent;
        border: none;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 12px;
        margin: 6px 0 6px 0;
    }}
    QScrollBar::handle:vertical {{
        background: {scroll_handle};
        border-radius: 6px;
        min-height: 30px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
    QScrollBar:horizontal, QScrollBar::handle:horizontal,
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
        border: none;
        height: 0px;
        width: 0px;
    }}
    QLineEdit, QComboBox, QPlainTextEdit, QListWidget {{
        background: {field_bg};
        border: 1px solid {border};
        border-radius: 20px;
        color: {text_primary};
        padding: 8px 12px;
        selection-background-color: rgba(128, 128, 128, 0.20);
    }}
    QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QListWidget:focus {{
        border: 1px solid rgba(128, 128, 128, 0.28);
        background: {field_focus};
    }}
    QLineEdit::placeholder {{
        color: {text_secondary};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 26px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 7px solid {text_primary};
        margin-right: 10px;
    }}
    QAbstractItemView {{
        background: {surface};
        color: {text_primary};
        border: 1px solid {border};
        selection-background-color: rgba(128, 128, 128, 0.14);
        outline: none;
    }}
    QListWidget::item {{
        border-radius: 10px;
        margin: 1px 0;
        padding: 4px 8px;
    }}
    QListWidget::item:selected, QListWidget::item:hover {{
        background: {field_focus};
    }}
    QPlainTextEdit {{
        padding-top: 8px;
    }}
    QSlider::groove:horizontal {{
        height: 12px;
        border: none;
        border-radius: 6px;
        background: {field_focus};
    }}
    QSlider::sub-page:horizontal {{
        border: none;
        border-radius: 6px;
        background: {slider_fill};
    }}
    QSlider::add-page:horizontal {{
        border: none;
        border-radius: 6px;
        background: rgba(128, 128, 128, 0.10);
    }}
    QSlider::handle:horizontal {{
        background: {surface};
        border: none;
        width: 22px;
        margin: -5px 0;
        border-radius: 11px;
    }}
    QLabel#sectionEyebrow {{
        color: {text_secondary};
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }}
    QLabel#sectionTitle {{
        color: {text_primary};
        font-size: 22px;
        font-weight: 700;
    }}
    QLabel#sectionDescription {{
        color: {text_secondary};
        font-size: 11px;
    }}
    QLabel#valueBadge {{
        color: {text_primary};
        background: {field_focus};
        border: 1px solid {border};
        border-radius: 20px;
        padding: 6px 10px;
        font-weight: 600;
        min-width: 52px;
    }}
    QLabel#statusBadge {{
        color: {text_primary};
        background: {field_focus};
        border: 1px solid {border};
        border-radius: 14px;
        padding: 10px 12px;
        font-weight: 600;
    }}
    """


def color_from_hex(value: str) -> QColor:
    return QColor(value)
