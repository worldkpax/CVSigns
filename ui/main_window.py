from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path

import cv2
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QWidget,
)

from core.inference_worker import InferenceWorker
from core.model_manager import Detection, ModelManager
from core.settings import AppSettings
from core.video_source import VideoSource
from ui.theme import app_stylesheet
from ui.widgets.control_panel import ControlPanel
from ui.widgets.snapping_scroll_area import SnapScrollArea
from ui.widgets.video_display import VideoDisplayWidget


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self.video_source = VideoSource()
        self.device_probe = ModelManager()
        self.worker = InferenceWorker()
        self.capture_timer = QTimer(self)
        self.capture_timer.setInterval(30)
        self.capture_timer.timeout.connect(self._poll_source)

        self.last_rendered_frame = None
        self.last_detections: list[Detection] = []
        self.video_writer: cv2.VideoWriter | None = None
        self.recording_active = False
        self.processing_active = False
        self._last_model_ok = False
        self.recent_detection_history: deque[str] = deque(maxlen=20)

        self.video_display = VideoDisplayWidget()
        self.control_panel = ControlPanel(
            default_model_path=self.settings.model_path,
            devices=self.device_probe.available_devices(),
            confidence=self.settings.confidence_threshold,
            iou=self.settings.iou_threshold,
            default_device=self.settings.device,
        )
        self.status_label = QLabel("Инициализация...")
        self.status_label.setObjectName("statusBadge")

        self._build_ui()
        self._connect_signals()
        self._start_worker()
        self._attempt_initial_model_load()

    def _build_ui(self) -> None:
        self.setWindowTitle("CVSigns - Обнаружение российских дорожных знаков")
        initial_width = min(self.settings.window_width, 1180)
        initial_height = min(self.settings.window_height, 760)
        self.setFixedSize(initial_width, initial_height)
        color_scheme = QApplication.instance().styleHints().colorScheme()
        self.setStyleSheet(app_stylesheet(color_scheme))

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.video_display)
        splitter.addWidget(self._build_control_panel_scroll())
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(0)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([760, 320])

        root = QWidget()
        root.setObjectName("appRoot")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.addWidget(splitter)
        self.setCentralWidget(root)

        status_bar = QStatusBar()
        status_bar.setContentsMargins(12, 12, 12, 12)
        status_bar.addWidget(self.status_label, 1)
        self.setStatusBar(status_bar)

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        self.menuBar().addAction(exit_action)

    def _build_control_panel_scroll(self) -> QScrollArea:
        scroll = SnapScrollArea()
        self.control_panel.setMinimumWidth(320)
        self.control_panel.setMaximumWidth(320)
        scroll.setWidget(self.control_panel)
        return scroll

    def _connect_signals(self) -> None:
        self.control_panel.open_image_clicked.connect(self._open_image)
        self.control_panel.open_video_clicked.connect(self._open_video)
        self.control_panel.connect_camera_clicked.connect(self._open_camera)
        self.control_panel.start_clicked.connect(self.start_processing)
        self.control_panel.stop_clicked.connect(self.stop_processing)
        self.control_panel.save_frame_clicked.connect(self._save_current_frame)
        self.control_panel.toggle_recording_clicked.connect(self._toggle_recording)
        self.control_panel.model_path_changed.connect(self._on_model_path_changed)
        self.control_panel.thresholds_changed.connect(self._on_thresholds_changed)

        self.worker.frame_ready.connect(self._on_processed_frame)
        self.worker.status_message.connect(self._set_status)
        self.worker.error_occurred.connect(self._on_worker_error)
        self.worker.model_state_changed.connect(self._on_model_state_changed)

    def _start_worker(self) -> None:
        self.worker.start()
        self.worker.set_thresholds(
            self.settings.confidence_threshold,
            self.settings.iou_threshold,
        )
        self.worker.set_device(self.settings.device)

    def _attempt_initial_model_load(self) -> None:
        model_path = self.control_panel.model_path()
        self.worker.request_model_load(model_path)

    def _choose_model(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите локальную модель YOLO",
            str(Path.cwd() / "models"),
            "PyTorch model (*.pt)",
        )
        if not file_path:
            return
        self.control_panel.set_model_path(file_path)

    def _open_camera(self) -> None:
        self.stop_processing(silent=True)
        ok, message = self.video_source.open_camera(0)
        self._set_status(message)
        self.control_panel.log_event(message)
        if ok:
            success, frame, _ = self.video_source.read()
            if success and frame is not None:
                self.video_display.set_frame(frame)
            else:
                self.video_display.show_message("Камера подключена. Нажмите 'Старт'.")

    def _open_video(self) -> None:
        self.stop_processing(silent=True)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть видео",
            str(Path.cwd()),
            "Видео (*.mp4 *.avi *.mov *.mkv *.mpeg)",
        )
        if not file_path:
            return
        ok, message = self.video_source.open_video(file_path)
        self._set_status(message)
        self.control_panel.log_event(message)
        if ok:
            self.video_display.show_message("Видео загружено. Нажмите 'Старт'.")

    def _open_image(self) -> None:
        self.stop_processing(silent=True)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть изображение",
            str(Path.cwd()),
            "Изображения (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if not file_path:
            return
        ok, message = self.video_source.open_image(file_path)
        self._set_status(message)
        self.control_panel.log_event(message)
        if ok:
            success, frame, _ = self.video_source.read()
            if success and frame is not None:
                self.video_display.set_frame(frame)

    def start_processing(self) -> None:
        if not self._last_model_ok:
            self._show_error(
                "Модель не загружена",
                "Файл модели отсутствует или не был загружен. Поместите веса в "
                "`models/russian_traffic_signs.pt` или выберите `.pt` файл вручную.",
            )
            return

        if not self.video_source.has_source():
            self._show_error(
                "Источник не выбран",
                "Сначала откройте изображение, видеофайл или подключите веб-камеру.",
            )
            return

        self.processing_active = True
        self.worker.clear_pending_frame()
        self.worker.set_active(True, emit_status=False)
        if self.video_source.source_type in {"camera", "video"}:
            self.capture_timer.start()
        elif self.video_source.source_type == "image":
            success, frame, _ = self.video_source.read()
            if success and frame is not None:
                self.worker.submit_frame(frame)
        self._set_status("Обработка запущена.")
        self.control_panel.log_event("Обработка запущена.")

    def stop_processing(self, silent: bool = False) -> None:
        was_active = self.processing_active or self.capture_timer.isActive() or self.recording_active
        self.processing_active = False
        self.capture_timer.stop()
        self.worker.set_active(False, emit_status=not silent)
        self.worker.clear_pending_frame()
        self._stop_recording_if_needed()
        if not silent and was_active:
            self._set_status("Обработка остановлена.")
            self.control_panel.log_event("Обработка остановлена.")

    def _poll_source(self) -> None:
        if not self.processing_active:
            return

        success, frame, end_of_stream = self.video_source.read()
        if not success or frame is None:
            if end_of_stream:
                self.stop_processing()
                self._set_status("Видео завершено.")
                self.control_panel.log_event("Видео завершено.")
                return
            self._set_status("Ошибка чтения кадра.")
            self.control_panel.log_event("Ошибка чтения кадра.")
            return

        self.worker.submit_frame(frame)

    def _on_processed_frame(
        self, frame, detections: list[Detection], fps: float
    ) -> None:
        self.last_rendered_frame = frame
        self.last_detections = detections
        self.video_display.set_frame(frame)
        for detection in detections:
            self.recent_detection_history.appendleft(
                f"{detection.class_name} | conf={detection.confidence:.2f}"
            )
        self.control_panel.update_detection_summary(list(self.recent_detection_history))
        self.control_panel.set_object_count(len(detections))
        self.control_panel.set_fps(fps)

        if self.recording_active:
            self._write_video_frame(frame)

    def _on_model_path_changed(self, model_path: str) -> None:
        self.settings.model_path = model_path
        if model_path:
            self.worker.request_model_load(model_path)

    def _on_thresholds_changed(self, confidence: float, iou: float) -> None:
        self.settings.confidence_threshold = confidence
        self.settings.iou_threshold = iou
        self.worker.set_thresholds(confidence, iou)

    def _on_device_changed(self, device: str) -> None:
        self.settings.device = device
        self.worker.set_device(device)

    def _on_model_state_changed(self, success: bool, message: str) -> None:
        self._last_model_ok = success
        self._set_status(message)
        self.control_panel.log_event(message)

    def _on_worker_error(self, message: str) -> None:
        self._set_status(message)
        self.control_panel.log_event(message)

    def _toggle_recording(self) -> None:
        if self.recording_active:
            self._stop_recording_if_needed()
            self.control_panel.set_recording_state(False)
            self._set_status("Запись обработанного видео остановлена.")
            self.control_panel.log_event("Запись обработанного видео остановлена.")
            return

        if self.last_rendered_frame is None:
            self._show_error(
                "Нет кадра для записи",
                "Сначала запустите обработку и дождитесь появления обработанного кадра.",
            )
            return

        output_dir = Path.cwd() / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"processed_{timestamp}.mp4"

        height, width = self.last_rendered_frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        fps = self.video_source.fps()
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        if not writer.isOpened():
            writer.release()
            self._show_error("Ошибка записи", "Не удалось создать файл для записи видео.")
            return

        self.video_writer = writer
        self.recording_active = True
        self.control_panel.set_recording_state(True)
        self._set_status(f"Запись видео: {output_path.name}")
        self.control_panel.log_event(f"Запись видео: {output_path}")

    def _write_video_frame(self, frame) -> None:
        if self.video_writer is None:
            return
        self.video_writer.write(frame)

    def _stop_recording_if_needed(self) -> None:
        if self.video_writer is not None:
            self.video_writer.release()
        self.video_writer = None
        self.recording_active = False
        self.control_panel.set_recording_state(False)

    def _save_current_frame(self) -> None:
        if self.last_rendered_frame is None:
            self._show_error(
                "Нет кадра",
                "Нечего сохранять. Сначала откройте источник и запустите обработку.",
            )
            return

        output_dir = Path.cwd() / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = output_dir / f"frame_{timestamp}.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить текущий кадр",
            str(default_path),
            "PNG (*.png);;JPEG (*.jpg *.jpeg)",
        )
        if not file_path:
            return

        if cv2.imwrite(file_path, self.last_rendered_frame):
            self._set_status(f"Кадр сохранен: {Path(file_path).name}")
            self.control_panel.log_event(f"Кадр сохранен: {file_path}")
        else:
            self._show_error("Ошибка сохранения", "Не удалось сохранить текущий кадр.")

    def _set_status(self, message: str) -> None:
        self.status_label.setText(message)

    def _show_error(self, title: str, message: str) -> None:
        self._set_status(message)
        self.control_panel.log_event(message)
        QMessageBox.critical(self, title, message)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.stop_processing(silent=True)
        self.video_source.close()
        self.worker.requestInterruption()
        self.worker.wait(3000)
        self.settings.save("config.json")
        super().closeEvent(event)
