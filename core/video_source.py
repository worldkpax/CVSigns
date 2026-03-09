from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class VideoSource:
    def __init__(self) -> None:
        self.capture: cv2.VideoCapture | None = None
        self.source_type: str | None = None
        self.source_path: str | None = None
        self.image_frame: np.ndarray | None = None
        self.camera_index: int = 0

    def open_camera(self, index: int = 0) -> tuple[bool, str]:
        self.close()
        capture = cv2.VideoCapture(index)
        if not capture.isOpened():
            capture.release()
            return False, f"Не удалось подключить камеру с индексом {index}."

        self.capture = capture
        self.source_type = "camera"
        self.source_path = None
        self.camera_index = index
        self.image_frame = None
        return True, f"Камера подключена: индекс {index}"

    def open_video(self, path: str) -> tuple[bool, str]:
        self.close()
        capture = cv2.VideoCapture(path)
        if not capture.isOpened():
            capture.release()
            return False, f"Не удалось открыть видео: {path}"

        self.capture = capture
        self.source_type = "video"
        self.source_path = path
        self.image_frame = None
        return True, f"Видео открыто: {Path(path).name}"

    def open_image(self, path: str) -> tuple[bool, str]:
        self.close()
        frame = cv2.imread(path)
        if frame is None:
            return False, f"Не удалось открыть изображение: {path}"

        self.source_type = "image"
        self.source_path = path
        self.image_frame = frame
        return True, f"Изображение открыто: {Path(path).name}"

    def read(self) -> tuple[bool, np.ndarray | None, bool]:
        if self.source_type == "image":
            if self.image_frame is None:
                return False, None, False
            return True, self.image_frame.copy(), False

        if self.capture is None:
            return False, None, False

        success, frame = self.capture.read()
        if not success or frame is None:
            return False, None, self.source_type == "video"
        return True, frame, False

    def fps(self) -> float:
        if self.capture is None:
            return 0.0
        fps = float(self.capture.get(cv2.CAP_PROP_FPS))
        return fps if fps > 1.0 else 25.0

    def frame_size(self) -> tuple[int, int]:
        if self.source_type == "image" and self.image_frame is not None:
            height, width = self.image_frame.shape[:2]
            return width, height

        if self.capture is None:
            return 0, 0

        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return width, height

    def has_source(self) -> bool:
        return self.source_type is not None

    def close(self) -> None:
        if self.capture is not None:
            self.capture.release()
        self.capture = None
        self.source_type = None
        self.source_path = None
        self.image_frame = None
