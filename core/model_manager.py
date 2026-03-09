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
        results = self.model.predict(
            source=frame,
            conf=confidence_threshold,
            iou=iou_threshold,
            device=resolved_device,
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
