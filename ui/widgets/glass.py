from __future__ import annotations

from PySide6.QtCore import QEasingCurve, Property, QPropertyAnimation, Qt, QVariantAnimation
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

def _rgba(color: QColor) -> str:
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"


class GlassCard(QFrame):
    def __init__(self, title: str | None = None, description: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("glassCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(14)

        self.setStyleSheet(
            """
            QFrame#glassCard {
                background: rgba(255, 255, 255, 0.10);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 22px;
            }
            """
        )

        if title:
            eyebrow = QLabel("SECTION")
            eyebrow.setObjectName("sectionEyebrow")
            eyebrow.setText(title.upper())
            self._layout.addWidget(eyebrow)
        if description:
            text = QLabel(description)
            text.setObjectName("sectionDescription")
            text.setWordWrap(True)
            self._layout.addWidget(text)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._layout


class AnimatedButton(QPushButton):
    def __init__(
        self,
        text: str,
        *,
        tone: str = "neutral",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_Hover, True)

        color_scheme = QApplication.instance().styleHints().colorScheme()
        is_dark = color_scheme != Qt.ColorScheme.Light

        if tone == "success":
            self._base = QColor(104, 188, 120, 230) if not is_dark else QColor(70, 150, 88, 235)
            self._hover = QColor(92, 176, 108, 245) if not is_dark else QColor(82, 162, 100, 245)
            self._text = QColor(250, 250, 250)
            self._border = QColor(69, 135, 80, 30)
        elif tone == "danger":
            self._base = QColor(221, 108, 108, 230) if not is_dark else QColor(168, 72, 72, 235)
            self._hover = QColor(209, 96, 96, 245) if not is_dark else QColor(180, 84, 84, 245)
            self._text = QColor(250, 250, 250)
            self._border = QColor(130, 40, 40, 28)
        elif is_dark:
            self._base = QColor(255, 255, 255, 26)
            self._hover = QColor(255, 255, 255, 38)
            self._text = QColor(245, 245, 245)
            self._border = QColor(255, 255, 255, 34)
        else:
            self._base = QColor(0, 0, 0, 8)
            self._hover = QColor(0, 0, 0, 14)
            self._text = QColor(17, 17, 19)
            self._border = QColor(17, 17, 19, 12)

        self._fill = self._base
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(180)
        self._animation.setEasingCurve(QEasingCurve.OutCubic)
        self._animation.valueChanged.connect(self._on_color_changed)
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"""
            QPushButton {{
                background: {_rgba(self._fill)};
                color: {_rgba(self._text)};
                border: 1px solid {_rgba(self._border)};
                border-radius: 20px;
                padding: 7px 10px;
                font-size: 12px;
                font-weight: 650;
            }}
            """
        )

    def _on_color_changed(self, value: QColor) -> None:
        self._fill = value
        self._apply_style()

    def _animate_to(self, target: QColor) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._fill)
        self._animation.setEndValue(target)
        self._animation.start()

    def enterEvent(self, event) -> None:
        self._animate_to(self._hover)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate_to(self._base)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        self._animate_to(self._hover.darker(108))
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        target = self._hover if self.rect().contains(event.position().toPoint()) else self._base
        self._animate_to(target)
        super().mouseReleaseEvent(event)


class AnimatedValueLabel(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._opacity = 1.0
        self._is_dark = QApplication.instance().styleHints().colorScheme() != Qt.ColorScheme.Light
        self._anim = QPropertyAnimation(self, b"labelOpacity", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.setObjectName("metricValue")
        self._apply_style()

    def _apply_style(self) -> None:
        alpha = int(max(0.0, min(1.0, self._opacity)) * 255)
        self.setStyleSheet(
            f"""
            QLabel#metricValue {{
                color: rgba({245 if self._is_dark else 18}, {245 if self._is_dark else 18}, {245 if self._is_dark else 18}, {alpha});
                font-size: 20px;
                font-weight: 700;
            }}
            """
        )

    def get_label_opacity(self) -> float:
        return self._opacity

    def set_label_opacity(self, value: float) -> None:
        self._opacity = value
        self._apply_style()

    labelOpacity = Property(float, get_label_opacity, set_label_opacity)

    def set_animated_text(self, text: str) -> None:
        if text == self.text():
            return
        self._anim.stop()
        self._anim.setStartValue(0.35)
        self._anim.setEndValue(1.0)
        self.setText(text)
        self._anim.start()


class MetricCard(GlassCard):
    def __init__(self, title: str, value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(2)
        self.setMaximumHeight(58)

        title_label = QLabel(title)
        title_label.setObjectName("sectionDescription")
        self.value_label = AnimatedValueLabel(value)

        self.content_layout.addWidget(title_label)
        self.content_layout.addWidget(self.value_label)

    def set_value(self, value: str) -> None:
        self.value_label.set_animated_text(value)
