from __future__ import annotations

import numpy as np
from PySide6.QtCore import QMutex, QMutexLocker, QThread, Signal

from core.frame_renderer import FrameRenderer
from core.model_manager import ModelManager


class InferenceWorker(QThread):
    frame_ready = Signal(object, object, float)
    status_message = Signal(str)
    error_occurred = Signal(str)
    model_state_changed = Signal(bool, str)

    def __init__(self) -> None:
        super().__init__()
        self._mutex = QMutex()
        self._latest_frame: np.ndarray | None = None
        self._active = False
        self._confidence_threshold = 0.25
        self._iou_threshold = 0.45
        self._device = "auto"
        self._pending_model_path: str | None = None
        self._model_manager = ModelManager()
        self._renderer = FrameRenderer()

    def run(self) -> None:
        while not self.isInterruptionRequested():
            pending_model_path = self._take_pending_model_path()
            if pending_model_path:
                success, message = self._model_manager.load_model(pending_model_path)
                self.model_state_changed.emit(success, message)
                self.status_message.emit(message)

            if not self._active:
                self.msleep(20)
                continue

            frame = self._take_latest_frame()
            if frame is None:
                self.msleep(5)
                continue

            if not self._model_manager.is_loaded():
                self.error_occurred.emit(
                    "Модель не загружена. Укажите корректный .pt файл и загрузите модель."
                )
                self._active = False
                continue

            try:
                started = self._perf_counter()
                confidence_threshold, iou_threshold, device = self._take_runtime_settings()
                detections = self._model_manager.predict(
                    frame=frame,
                    confidence_threshold=confidence_threshold,
                    iou_threshold=iou_threshold,
                    device=device,
                )
                rendered = self._renderer.render(frame, detections)
                elapsed = max(self._perf_counter() - started, 1e-6)
                fps = 1.0 / elapsed
                self.frame_ready.emit(rendered, detections, fps)
            except Exception as exc:
                self.error_occurred.emit(f"Ошибка инференса: {exc}")
                self.msleep(50)

    def request_model_load(self, model_path: str) -> None:
        locker = QMutexLocker(self._mutex)
        self._pending_model_path = model_path
        del locker

    def set_thresholds(self, confidence_threshold: float, iou_threshold: float) -> None:
        locker = QMutexLocker(self._mutex)
        self._confidence_threshold = confidence_threshold
        self._iou_threshold = iou_threshold
        del locker

    def set_device(self, device: str) -> None:
        locker = QMutexLocker(self._mutex)
        self._device = device
        del locker
        resolved = self._model_manager.resolve_device(device)
        self.status_message.emit(f"Устройство инференса: {resolved}")

    def configure_tiling(
        self,
        enabled: bool,
        tile_size: int,
        tile_overlap: float,
        tile_min_side: int,
    ) -> None:
        self._model_manager.configure_tiling(
            enabled=enabled,
            tile_size=tile_size,
            tile_overlap=tile_overlap,
            tile_min_side=tile_min_side,
        )

    def set_tiling_enabled(self, enabled: bool) -> None:
        self._model_manager.set_tiling_enabled(enabled)

    def set_active(self, active: bool, emit_status: bool = True) -> None:
        self._active = active
        if emit_status:
            state = "запущена" if active else "остановлена"
            self.status_message.emit(f"Обработка {state}.")

    def submit_frame(self, frame: np.ndarray) -> None:
        locker = QMutexLocker(self._mutex)
        self._latest_frame = frame.copy()
        del locker

    def clear_pending_frame(self) -> None:
        locker = QMutexLocker(self._mutex)
        self._latest_frame = None
        del locker

    def _take_latest_frame(self) -> np.ndarray | None:
        locker = QMutexLocker(self._mutex)
        if self._latest_frame is None:
            del locker
            return None
        frame = self._latest_frame
        self._latest_frame = None
        del locker
        return frame

    def _take_pending_model_path(self) -> str | None:
        locker = QMutexLocker(self._mutex)
        pending_model_path = self._pending_model_path
        self._pending_model_path = None
        del locker
        return pending_model_path

    def _take_runtime_settings(self) -> tuple[float, float, str]:
        locker = QMutexLocker(self._mutex)
        confidence_threshold = self._confidence_threshold
        iou_threshold = self._iou_threshold
        device = self._device
        del locker
        return confidence_threshold, iou_threshold, device

    @staticmethod
    def _perf_counter() -> float:
        import time

        return time.perf_counter()
