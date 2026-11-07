"""Detect actual image inputs using explicitly supplied YOLO weights."""
from collections import Counter
from pathlib import Path


class ObjectDetector:
    """Reuse one model instance across images."""

    def __init__(self, weights: str, confidence: float = 0.25):
        if not Path(weights).is_file():
            raise FileNotFoundError(f"Model weights not found: {weights}")
        if not 0 < confidence <= 1:
            raise ValueError("Confidence must be in (0, 1].")
        from ultralytics import YOLO
        self.model = YOLO(str(Path(weights).resolve()))
        self.confidence = confidence

    def detect(self, image_path: str) -> list[dict]:
        """Return class names, confidence scores and xyxy pixel coordinates."""
        if not Path(image_path).is_file():
            raise FileNotFoundError(f"Image not found: {image_path}")
        result = self.model.predict(source=str(Path(image_path).resolve()),
                                    conf=self.confidence, verbose=False)[0]
        if result.boxes is None or len(result.boxes) == 0:
            return []
        return [
            {"name": result.names[int(class_id)], "confidence": float(score),
             "box": [float(value) for value in box]}
            for class_id, score, box in zip(result.boxes.cls.cpu().tolist(),
                                             result.boxes.conf.cpu().tolist(),
                                             result.boxes.xyxy.cpu().tolist())
        ]

    def summary(self, image_path: str) -> str:
        """Count every detected category without inventing missing detections."""
        counts = Counter(item["name"] for item in self.detect(image_path))
        return ', '.join(f'{count} {name}' for name, count in sorted(counts.items())) or 'no detections'

    def top1(self, image_path: str) -> str:
        """Return the most confident object, or an empty string."""
        detections = self.detect(image_path)
        return max(detections, key=lambda item: item['confidence'])['name'] if detections else ''
