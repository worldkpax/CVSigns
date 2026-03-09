from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.glass import AnimatedButton, MetricCard


class ControlPanel(QWidget):
    select_model_clicked = Signal()
    open_image_clicked = Signal()
    open_video_clicked = Signal()
    connect_camera_clicked = Signal()
    start_clicked = Signal()
    stop_clicked = Signal()
    save_frame_clicked = Signal()
    toggle_recording_clicked = Signal()
    model_path_changed = Signal(str)
    thresholds_changed = Signal(float, float)
    device_changed = Signal(str)

    def __init__(
        self,
        default_model_path: str,
        devices: list[str],
        confidence: float,
        iou: float,
        default_device: str,
    ) -> None:
        super().__init__()
        self.setObjectName("controlPanelRoot")
        self._model_path = default_model_path
        self.cards: list[QFrame] = []
        self._build_ui(default_model_path, devices, confidence, iou, default_device)
        self._connect_signals()

    def _build_ui(
        self,
        default_model_path: str,
        devices: list[str],
        confidence: float,
        iou: float,
        default_device: str,
    ) -> None:
        compact_card_height = 92

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        self.controls_card = self._build_controls_card()
        self.settings_card = self._build_settings_card(
            devices, confidence, iou, default_device, compact_card_height
        )
        self.metrics_card = self._build_metrics_card(compact_card_height)
        self.detections_card = self._build_detections_card()
        self.log_card = self._build_log_card()

        root.addWidget(self.controls_card)
        root.addWidget(self.settings_card)
        root.addWidget(self.metrics_card)
        root.addWidget(self.detections_card)
        root.addWidget(self.log_card, 1)

    def _build_controls_card(self) -> QFrame:
        card = self._make_card("Управление")
        layout = card.layout()

        self.camera_button = AnimatedButton("Камера")
        self.video_button = AnimatedButton("Видео")
        self.image_button = AnimatedButton("Фото")
        self.start_button = AnimatedButton("Старт", tone="success")
        self.stop_button = AnimatedButton("Стоп", tone="danger")
        self.save_frame_button = AnimatedButton("Снимок")
        self.record_button = AnimatedButton("Запись")

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.addWidget(self.camera_button, 0, 0)
        grid.addWidget(self.video_button, 0, 1)
        grid.addWidget(self.image_button, 1, 0)
        grid.addWidget(self.start_button, 1, 1)
        grid.addWidget(self.stop_button, 2, 0)
        grid.addWidget(self.save_frame_button, 2, 1)
        grid.addWidget(self.record_button, 3, 0, 1, 2)

        layout.addLayout(grid)
        return card

    def _build_settings_card(
        self,
        devices: list[str],
        confidence: float,
        iou: float,
        default_device: str,
        card_height: int,
    ) -> QFrame:
        card = self._make_card("Параметры")
        layout = card.layout()

        self.confidence_slider = QSlider(Qt.Horizontal)
        self.confidence_slider.setRange(1, 100)
        self.confidence_slider.setValue(int(confidence * 100))
        self.confidence_value = QLabel(f"{confidence:.2f}")
        self.confidence_value.setObjectName("valueBadge")
        self.confidence_value.setAlignment(Qt.AlignCenter)
        self.confidence_value.setFixedSize(72, 30)

        self.iou_slider = QSlider(Qt.Horizontal)
        self.iou_slider.setRange(1, 100)
        self.iou_slider.setValue(int(iou * 100))
        self.iou_value = QLabel(f"{iou:.2f}")
        self.iou_value.setObjectName("valueBadge")
        self.iou_value.setAlignment(Qt.AlignCenter)
        self.iou_value.setFixedSize(72, 30)

        settings_grid = QGridLayout()
        settings_grid.setHorizontalSpacing(5)
        settings_grid.setVerticalSpacing(4)
        settings_grid.setColumnStretch(0, 0)
        settings_grid.setColumnStretch(1, 1)
        settings_grid.setColumnStretch(2, 0)
        settings_grid.addWidget(self._field_label("Confidence"), 0, 0)
        settings_grid.addWidget(self.confidence_slider, 0, 1)
        settings_grid.addWidget(self.confidence_value, 0, 2)
        settings_grid.addWidget(self._field_label("IoU"), 1, 0)
        settings_grid.addWidget(self.iou_slider, 1, 1)
        settings_grid.addWidget(self.iou_value, 1, 2)

        layout.addLayout(settings_grid)
        self.confidence_value.setStyleSheet(
            """
            QLabel {
                background: rgba(0, 0, 0, 0.05);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 11px;
                padding: 2px 8px;
                min-width: 72px;
                max-width: 72px;
                font-size: 11px;
            }
            """
        )
        self.iou_value.setStyleSheet(
            """
            QLabel {
                background: rgba(0, 0, 0, 0.05);
                border: 1px solid rgba(0, 0, 0, 0.08);
                border-radius: 11px;
                padding: 2px 8px;
                min-width: 72px;
                max-width: 72px;
                font-size: 11px;
            }
            """
        )
        card.setFixedHeight(card_height)
        return card

    def _build_metrics_card(self, card_height: int) -> QFrame:
        card = self._make_card("Метрики")
        layout = card.layout()

        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(8)
        self.object_count_card = MetricCard("Объектов", "0")
        self.fps_card = MetricCard("FPS", "0.0")
        metrics_row.addWidget(self.object_count_card)
        metrics_row.addWidget(self.fps_card)

        layout.addLayout(metrics_row)
        card.setFixedHeight(card_height)
        return card

    def _build_detections_card(self) -> QFrame:
        card = self._make_card("Объекты")
        layout = card.layout()
        self.detections_list = QListWidget()
        self.detections_list.setAlternatingRowColors(False)
        self.detections_list.setMinimumHeight(172)
        self.detections_list.setMaximumHeight(172)
        layout.addWidget(self.detections_list)
        card.setFixedHeight(210)
        return card

    def _build_log_card(self) -> QFrame:
        card = self._make_card("Лог событий")
        layout = card.layout()
        self.log_edit = QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(108)
        self.log_edit.setMaximumHeight(108)
        layout.addWidget(self.log_edit)
        card.setFixedHeight(146)
        return card

    def _make_card(self, title: str | None = None, description: str | None = None) -> QFrame:
        card = QFrame()
        card.setObjectName("panelCard")
        card.setStyleSheet(
            """
            QFrame#panelCard {
                background: rgba(0, 0, 0, 0.035);
                border: 1px solid rgba(0, 0, 0, 0.04);
                border-radius: 30px;
            }
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)

        if title:
            eyebrow = QLabel(title.upper())
            eyebrow.setObjectName("sectionEyebrow")
            layout.addWidget(eyebrow)
        if description:
            description_label = QLabel(description)
            description_label.setObjectName("sectionDescription")
            description_label.setWordWrap(True)
            layout.addWidget(description_label)
        self.cards.append(card)
        return card

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionDescription")
        return label

    def _connect_signals(self) -> None:
        self.camera_button.clicked.connect(self.connect_camera_clicked)
        self.video_button.clicked.connect(self.open_video_clicked)
        self.image_button.clicked.connect(self.open_image_clicked)
        self.start_button.clicked.connect(self.start_clicked)
        self.stop_button.clicked.connect(self.stop_clicked)
        self.save_frame_button.clicked.connect(self.save_frame_clicked)
        self.record_button.clicked.connect(self.toggle_recording_clicked)
        self.confidence_slider.valueChanged.connect(self._emit_thresholds)
        self.iou_slider.valueChanged.connect(self._emit_thresholds)

    def _emit_thresholds(self) -> None:
        confidence = self.confidence_slider.value() / 100.0
        iou = self.iou_slider.value() / 100.0
        self.confidence_value.setText(f"{confidence:.2f}")
        self.iou_value.setText(f"{iou:.2f}")
        self.thresholds_changed.emit(confidence, iou)

    def model_path(self) -> str:
        return self._model_path.strip()

    def set_model_path(self, path: str) -> None:
        self._model_path = path
        self.model_path_changed.emit(path)

    def update_detection_summary(self, items: list[str]) -> None:
        self.detections_list.clear()
        if not items:
            self.detections_list.addItem(QListWidgetItem("Сейчас объектов нет"))
            return
        for item in items[:10]:
            self.detections_list.addItem(QListWidgetItem(item))

    def set_object_count(self, count: int) -> None:
        self.object_count_card.set_value(str(count))

    def set_fps(self, fps: float) -> None:
        self.fps_card.set_value(f"{fps:.1f}")

    def log_event(self, message: str) -> None:
        self.log_edit.appendPlainText(message)

    def set_recording_state(self, is_recording: bool) -> None:
        self.record_button.setText(
            "Стоп запись" if is_recording else "Запись"
        )
