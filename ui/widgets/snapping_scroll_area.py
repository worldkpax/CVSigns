from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, QTimer, Qt
from PySide6.QtWidgets import QAbstractSlider, QFrame, QScrollArea, QWidget


class SnapScrollArea(QScrollArea):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._snap_timer = QTimer(self)
        self._snap_timer.setSingleShot(True)
        self._snap_timer.setInterval(180)
        self._snap_timer.timeout.connect(self._snap_to_nearest_card)

        self._scroll_animation = QPropertyAnimation(
            self.verticalScrollBar(),
            b"value",
            self,
        )
        self._scroll_animation.setDuration(260)
        self._scroll_animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._scroll_animation.finished.connect(self._on_animation_finished)
        self._snap_enabled = True

        self.setFrameShape(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.horizontalScrollBar().setEnabled(False)
        self.verticalScrollBar().valueChanged.connect(self._schedule_snap)
        self.viewport().installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.viewport() and event.type() == QEvent.Resize:
            self._schedule_snap()
        return super().eventFilter(watched, event)

    def wheelEvent(self, event) -> None:
        super().wheelEvent(event)
        self._schedule_snap()

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self._schedule_snap()

    def setWidget(self, widget: QWidget) -> None:
        super().setWidget(widget)
        widget.installEventFilter(self)

    def _schedule_snap(self) -> None:
        if not self._snap_enabled:
            return
        slider = self.verticalScrollBar()
        if slider.maximum() <= 0:
            return
        if slider.isSliderDown():
            return
        if slider.isVisible() and slider.repeatAction() != QAbstractSlider.SliderNoAction:
            return
        self._snap_timer.start()

    def _card_positions(self) -> list[int]:
        widget = self.widget()
        if widget is None:
            return []

        positions: list[int] = [0]
        for child in widget.findChildren(QFrame):
            if child.parentWidget() is widget and child.objectName() == "panelCard":
                positions.append(child.y())

        max_scroll = self.verticalScrollBar().maximum()
        if max_scroll > 0:
            positions.append(max_scroll)
        return sorted(set(min(max(pos, 0), max_scroll) for pos in positions))

    def _snap_to_nearest_card(self) -> None:
        positions = self._card_positions()
        if not positions:
            return

        slider = self.verticalScrollBar()
        current = slider.value()
        target = min(positions, key=lambda pos: abs(pos - current))
        if abs(target - current) <= 2:
            return

        self._snap_enabled = False
        self._scroll_animation.stop()
        self._scroll_animation.setStartValue(current)
        self._scroll_animation.setEndValue(target)
        self._scroll_animation.start()

    def _on_animation_finished(self) -> None:
        self._snap_enabled = True
