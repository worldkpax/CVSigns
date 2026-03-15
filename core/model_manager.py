from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from ultralytics import YOLO


@dataclass(slots=True)
class Detection:
    class_id: int
    class_name: str
    confidence: float
    bbox: tuple[int, int, int, int]


class ModelManager:
    def __init__(self) -> None:
        self.model: YOLO | None = None
        self.model_path: str | None = None
        self._class_names: dict[int, str] = {}
        self._tile_inference_enabled = True
        self._tile_size = 960
        self._tile_overlap = 0.25
        self._tile_min_side = 1200

    def configure_tiling(
        self,
        enabled: bool,
        tile_size: int,
        tile_overlap: float,
        tile_min_side: int,
    ) -> None:
        self._tile_inference_enabled = enabled
        self._tile_size = max(tile_size, 64)
        self._tile_overlap = min(max(tile_overlap, 0.0), 0.8)
        self._tile_min_side = max(tile_min_side, self._tile_size)

    def set_tiling_enabled(self, enabled: bool) -> None:
        self._tile_inference_enabled = enabled

    def load_model(self, model_path: str) -> tuple[bool, str]:
        path = Path(model_path)
        if not path.exists():
            self.model = None
            self.model_path = None
            self._class_names = {}
            return (
                False,
                f"Файл модели не найден: {path}. Поместите локальные веса YOLO в этот путь "
                "или выберите файл через кнопку 'Выбрать модель'.",
            )

        try:
            model = YOLO(str(path))
            self.model = model
            self.model_path = str(path)
            self._class_names = self._extract_class_names(model)
            return True, f"Модель загружена: {path}"
        except Exception as exc:
            self.model = None
            self.model_path = None
            self._class_names = {}
            return False, f"Не удалось загрузить модель: {exc}"

    def is_loaded(self) -> bool:
        return self.model is not None

    def available_devices(self) -> list[str]:
        devices = ["auto", "cpu"]
        if torch.cuda.is_available():
            devices.append("cuda")
        return devices

    def resolve_device(self, requested: str) -> str:
        if requested == "cuda" and not torch.cuda.is_available():
            return "cpu"
        if requested == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return requested

    def predict(
        self,
        frame: np.ndarray,
        confidence_threshold: float,
        iou_threshold: float,
        device: str,
    ) -> list[Detection]:
        if self.model is None:
            raise RuntimeError("Модель не загружена.")

        resolved_device = self.resolve_device(device)
        detections = self._predict_single(
            frame=frame,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            device=resolved_device,
        )

        if not self._should_use_tiling(frame):
            return detections

        tiled_detections: list[Detection] = []
        for tile_frame, offset_x, offset_y in self._generate_tiles(frame):
            for detection in self._predict_single(
                frame=tile_frame,
                confidence_threshold=confidence_threshold,
                iou_threshold=iou_threshold,
                device=resolved_device,
            ):
                tiled_detections.append(
                    Detection(
                        class_id=detection.class_id,
                        class_name=detection.class_name,
                        confidence=detection.confidence,
                        bbox=(
                            detection.bbox[0] + offset_x,
                            detection.bbox[1] + offset_y,
                            detection.bbox[2] + offset_x,
                            detection.bbox[3] + offset_y,
                        ),
                    )
                )

        return self._deduplicate_detections(
            detections + tiled_detections,
            iou_threshold=max(iou_threshold, 0.5),
        )

    def _predict_single(
        self,
        frame: np.ndarray,
        confidence_threshold: float,
        iou_threshold: float,
        device: str,
    ) -> list[Detection]:
        results = self.model.predict(
            source=frame,
            conf=confidence_threshold,
            iou=iou_threshold,
            device=device,
            verbose=False,
        )
        if not results:
            return []

        result = results[0]
        boxes = getattr(result, "boxes", None)
        if boxes is None or boxes.xyxy is None or len(boxes) == 0:
            return []

        xyxy = boxes.xyxy.detach().cpu().numpy()
        confs = boxes.conf.detach().cpu().numpy()
        classes = boxes.cls.detach().cpu().numpy().astype(int)

        detections: list[Detection] = []
        for box, conf, class_id in zip(xyxy, confs, classes):
            x1, y1, x2, y2 = [int(v) for v in box.tolist()]
            detections.append(
                Detection(
                    class_id=int(class_id),
                    class_name=self.get_class_name(int(class_id)),
                    confidence=float(conf),
                    bbox=(x1, y1, x2, y2),
                )
            )
        return detections

    def _should_use_tiling(self, frame: np.ndarray) -> bool:
        if not self._tile_inference_enabled:
            return False
        height, width = frame.shape[:2]
        return max(height, width) >= self._tile_min_side

    def _generate_tiles(
        self, frame: np.ndarray
    ) -> list[tuple[np.ndarray, int, int]]:
        height, width = frame.shape[:2]
        tile_size = min(self._tile_size, height, width)
        if tile_size <= 0:
            return []

        stride = max(int(tile_size * (1.0 - self._tile_overlap)), 1)
        y_positions = self._tile_positions(height, tile_size, stride)
        x_positions = self._tile_positions(width, tile_size, stride)

        tiles: list[tuple[np.ndarray, int, int]] = []
        for top in y_positions:
            for left in x_positions:
                bottom = min(top + tile_size, height)
                right = min(left + tile_size, width)
                tile = frame[top:bottom, left:right]
                if tile.size == 0:
                    continue
                tiles.append((tile, left, top))
        return tiles

    def _tile_positions(self, full_size: int, tile_size: int, stride: int) -> list[int]:
        if full_size <= tile_size:
            return [0]

        positions = list(range(0, full_size - tile_size + 1, stride))
        last_position = full_size - tile_size
        if positions[-1] != last_position:
            positions.append(last_position)
        return positions

    def _deduplicate_detections(
        self, detections: list[Detection], iou_threshold: float
    ) -> list[Detection]:
        if len(detections) < 2:
            return detections

        kept: list[Detection] = []
        grouped: dict[int, list[Detection]] = {}
        for detection in detections:
            grouped.setdefault(detection.class_id, []).append(detection)

        for class_detections in grouped.values():
            ordered = sorted(
                class_detections,
                key=lambda detection: detection.confidence,
                reverse=True,
            )
            while ordered:
                current = ordered.pop(0)
                kept.append(current)
                ordered = [
                    candidate
                    for candidate in ordered
                    if self._bbox_iou(current.bbox, candidate.bbox) < iou_threshold
                ]

        return kept

    def _bbox_iou(
        self,
        bbox_a: tuple[int, int, int, int],
        bbox_b: tuple[int, int, int, int],
    ) -> float:
        ax1, ay1, ax2, ay2 = bbox_a
        bx1, by1, bx2, by2 = bbox_b

        inter_x1 = max(ax1, bx1)
        inter_y1 = max(ay1, by1)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        intersection = inter_w * inter_h
        if intersection == 0:
            return 0.0

        area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
        area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
        union = area_a + area_b - intersection
        if union <= 0:
            return 0.0
        return intersection / union

    def get_class_name(self, class_id: int) -> str:
        return self._class_names.get(class_id, f"class_{class_id}")

    def _extract_class_names(self, model: YOLO) -> dict[int, str]:
        names: Any = getattr(model, "names", None)
        if isinstance(names, dict):
            normalized: dict[int, str] = {}
            for key, value in names.items():
                try:
                    class_id = int(key)
                except (TypeError, ValueError):
                    continue
                label = str(value).strip() if value is not None else ""
                normalized[class_id] = label or f"class_{class_id}"
            return normalized

        if isinstance(names, (list, tuple)):
            return {
                index: (str(value).strip() if str(value).strip() else f"class_{index}")
                for index, value in enumerate(names)
            }

        return {}
