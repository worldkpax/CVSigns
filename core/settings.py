from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class AppSettings:
    model_path: str = "models/russian_traffic_signs.pt"
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    device: str = "auto"
    window_width: int = 1400
    window_height: int = 860

    @classmethod
    def load(cls, path: str | Path) -> "AppSettings":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        defaults = asdict(cls())
        defaults.update(data)
        return cls(**defaults)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
