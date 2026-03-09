from __future__ import annotations

from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core.model_manager import Detection


class FrameRenderer:
    def __init__(self) -> None:
        self.palette = [
            (27, 158, 119),
            (217, 95, 2),
            (117, 112, 179),
            (231, 41, 138),
            (102, 166, 30),
            (230, 171, 2),
            (166, 118, 29),
            (102, 102, 102),
        ]
        self._font = self._load_font(18)

    def render(self, frame: np.ndarray, detections: list[Detection]) -> np.ndarray:
        canvas = frame.copy()
        for detection in detections:
            color = self.palette[detection.class_id % len(self.palette)]
            x1, y1, x2, y2 = detection.bbox
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
            canvas = self._draw_label(
                canvas,
                text=f"{detection.class_name} {detection.confidence:.2f}",
                anchor=(x1, y1),
                color=color,
            )
        return canvas

    def summarize(self, detections: list[Detection]) -> list[str]:
        counts = Counter(det.class_name for det in detections)
        return [f"{name}: {count}" for name, count in counts.most_common()]

    def _draw_label(
        self,
        frame: np.ndarray,
        text: str,
        anchor: tuple[int, int],
        color: tuple[int, int, int],
    ) -> np.ndarray:
        if self._font is None:
            return self._draw_label_cv(frame, text, anchor, color)

        x1, y1 = anchor
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb_frame)
        draw = ImageDraw.Draw(image)

        text_bbox = draw.textbbox((0, 0), text, font=self._font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        pad_x = 8
        pad_y = 5

        top = max(0, y1 - text_h - pad_y * 2 - 2)
        bottom = top + text_h + pad_y * 2
        right = x1 + text_w + pad_x * 2

        draw.rounded_rectangle(
            (x1, top, right, bottom),
            radius=8,
            fill=(color[2], color[1], color[0]),
        )
        draw.text(
            (x1 + pad_x, top + pad_y - 1),
            text,
            font=self._font,
            fill=(255, 255, 255),
        )
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    def _draw_label_cv(
        self,
        frame: np.ndarray,
        text: str,
        anchor: tuple[int, int],
        color: tuple[int, int, int],
    ) -> np.ndarray:
        x1, y1 = anchor
        safe_text = text.encode("ascii", errors="replace").decode("ascii")
        (text_w, text_h), baseline = cv2.getTextSize(
            safe_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2
        )
        text_y = max(y1, text_h + baseline + 8)
        cv2.rectangle(
            frame,
            (x1, text_y - text_h - baseline - 6),
            (x1 + text_w + 10, text_y + 4),
            color,
            thickness=-1,
        )
        cv2.putText(
            frame,
            safe_text,
            (x1 + 5, text_y - 4),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        return frame

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont | None:
        candidates = [
            Path("assets/fonts/DejaVuSans.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
            Path("/Library/Fonts/Arial Unicode.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
        ]
        for font_path in candidates:
            if not font_path.exists():
                continue
            try:
                return ImageFont.truetype(str(font_path), size=size)
            except Exception:
                continue
        return None
