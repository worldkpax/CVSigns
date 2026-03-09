from __future__ import annotations

import cv2
from PySide6.QtGui import QImage, QPixmap


def cv_to_qpixmap(frame) -> QPixmap:
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width, channels = rgb_frame.shape
    bytes_per_line = channels * width
    image = QImage(
        rgb_frame.data,
        width,
        height,
        bytes_per_line,
        QImage.Format_RGB888,
    )
    return QPixmap.fromImage(image.copy())
