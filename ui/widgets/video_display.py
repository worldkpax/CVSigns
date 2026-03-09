from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from utils.image_utils import cv_to_qpixmap


class VideoDisplayWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._pixmap: QPixmap | None = None
        self._is_dark = QApplication.instance().styleHints().colorScheme() != Qt.ColorScheme.Light

        self.frame_shell = QFrame()
        self.frame_shell.setObjectName("videoShell")
        self.frame_shell.setStyleSheet(self._shell_stylesheet())

        self.overlay_eyebrow = QLabel("LIVE PREVIEW")
        self.overlay_eyebrow.setObjectName("sectionEyebrow")
        self.overlay_title = QLabel("Обработанный видеопоток")
        self.overlay_title.setObjectName("sectionTitle")
        self.overlay_description = QLabel(
            "Здесь отображается поток с детекцией знаков и предпросмотром результата."
        )
        self.overlay_description.setObjectName("sectionDescription")
        self.overlay_description.setWordWrap(True)

        self.image_label = QLabel("Выберите источник и загрузите модель.")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setWordWrap(True)
        self.image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_label.setMinimumSize(280, 200)
        self.image_label.setScaledContents(False)
        self.image_label.setStyleSheet(self._image_stylesheet())

        shell_layout = QVBoxLayout(self.frame_shell)
        shell_layout.setContentsMargins(10, 10, 10, 10)
        shell_layout.setSpacing(8)
        shell_layout.addWidget(self.image_label, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.frame_shell)

    def _shell_stylesheet(self) -> str:
        if self._is_dark:
            return """
            QFrame#videoShell {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 0.09),
                    stop:1 rgba(255, 255, 255, 0.05)
                );
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 34px;
            }
            """
        return """
        QFrame#videoShell {
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(0, 0, 0, 0.04),
                stop:1 rgba(0, 0, 0, 0.02)
            );
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-radius: 34px;
        }
        """

    def _image_stylesheet(self) -> str:
        if self._is_dark:
            return """
            QLabel {
                background: rgba(15, 15, 16, 0.92);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 28px;
                color: rgba(245, 245, 245, 0.90);
                font-size: 18px;
                font-weight: 600;
                padding: 12px;
            }
            """
        return """
        QLabel {
            background: rgba(255, 255, 255, 0.94);
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-radius: 28px;
            color: rgba(20, 20, 22, 0.92);
            font-size: 18px;
            font-weight: 600;
            padding: 12px;
        }
        """

    def set_frame(self, frame: np.ndarray) -> None:
        self._pixmap = cv_to_qpixmap(frame)
        self._update_scaled_pixmap()

    def show_message(self, message: str) -> None:
        self._pixmap = None
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText(message)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def _update_scaled_pixmap(self) -> None:
        if self._pixmap is None:
            return
        target_size = self.image_label.size()
        if target_size.width() <= 1 or target_size.height() <= 1:
            target_size = self.frame_shell.size()
        if target_size.width() <= 1 or target_size.height() <= 1:
            return
        scaled = self._pixmap.scaled(
            target_size,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        self.image_label.setText("")
        self.image_label.setPixmap(self._rounded_pixmap(scaled, 28.0))

    def _rounded_pixmap(self, pixmap: QPixmap, radius: float) -> QPixmap:
        rounded = QPixmap(pixmap.size())
        rounded.fill(Qt.GlobalColor.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing, True)
        path = QPainterPath()
        path.addRoundedRect(rounded.rect(), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        return rounded
