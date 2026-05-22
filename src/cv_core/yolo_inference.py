# src/cv_core/yolo_inference.py
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
from dataclasses import dataclass, field
import numpy as np
import cv2
from ultralytics import YOLO
from loguru import logger


@dataclass
class Detection:
    """Базовая единица детекции UI-элемента."""
    class_id: int
    class_name: str
    confidence: float
    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2) в пикселях
    width: int
    height: int

    def center(self) -> tuple[float, float]:
        return (self.bbox[0] + self.bbox[2]) / 2.0, (self.bbox[1] + self.bbox[3]) / 2.0

    def to_dict(self) -> dict:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "width": self.width,
            "height": self.height
        }


@dataclass
class StructuralFeatures:
    """Структурные признаки, извлекаемые из детекций для агрегации."""
    detections: List[Detection]
    class_counts: Dict[str, int]
    total_objects: int
    bbox_coverage_ratio: float
    spatial_distribution: Dict[str, int]  # Распределение по квадрантам: TL, TR, BL, BR
    confidence_stats: Dict[str, float]    # mean, max, std, median

    def to_dict(self) -> dict:
        return {
            "detections": [d.to_dict() for d in self.detections],
            "class_counts": self.class_counts,
            "total_objects": self.total_objects,
            "bbox_coverage_ratio": round(self.bbox_coverage_ratio, 4),
            "spatial_distribution": self.spatial_distribution,
            "confidence_stats": {k: round(v, 4) for k, v in self.confidence_stats.items()}
        }


class YOLOInferenceEngine:
    """
    Ядро инференса YOLOv8 для детекции UI-элементов.
    Возвращает сырые детекции + структурные признаки для гибридного агрегатора.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config.get("yolo", {})
        self.paths = config.get("paths", {})
        self.model_path = Path(self.paths.get("yolo_model", "models/best.pt"))
        self._validate_config()
        self._load_model()

    def _validate_config(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"YOLO model not found at: {self.model_path}")
        required = {"classes", "conf_threshold", "iou_threshold", "imgsz"}
        missing = required - set(self.config.keys())
        if missing:
            raise ValueError(f"Missing YOLO config keys: {missing}")

    def _load_model(self):
        logger.info(f"Loading YOLOv8 model from {self.model_path}")
        self.model = YOLO(str(self.model_path))
        # Явная настройка параметров инференса
        self.model.overrides.update({
            "conf": self.config["conf_threshold"],
            "iou": self.config["iou_threshold"],
            "imgsz": self.config["imgsz"],
            "device": self.config.get("device", "cpu"),
            "half": self.config.get("half_precision", False),
            "verbose": False
        })

    def predict(self, image_input: Union[str, Path, np.ndarray]) -> StructuralFeatures:
        """
        Выполняет инференс и возвращает структурные признаки.
        :param image_input: путь к изображению или numpy-массив (BGR/RGB не важно, YOLO нормализует сам)
        """
        logger.debug("Starting YOLO inference...")
        
        results = self.model.predict(
            source=image_input,
            conf=self.config["conf_threshold"],
            iou=self.config["iou_threshold"],
            imgsz=self.config["imgsz"],
            device=self.config.get("device", "cpu"),
            half=self.config.get("half_precision", False),
            verbose=False
        )

        detections = self._extract_detections(results)
        img_w, img_h = self._get_image_shape(image_input)
        structural = self._compute_structural_features(detections, img_w, img_h)
        
        logger.info(
            f"Inference complete | Objects: {structural.total_objects} | "
            f"Coverage: {structural.bbox_coverage_ratio:.2%} | "
            f"Mean conf: {structural.confidence_stats['mean']:.3f}"
        )
        return structural

    def _get_image_shape(self, image_input: Union[str, Path, np.ndarray]) -> tuple[int, int]:
        if isinstance(image_input, (str, Path)):
            img = cv2.imread(str(image_input))
        else:
            img = image_input
        if img is None:
            raise ValueError("Failed to load/decode image for shape extraction")
        return img.shape[1], img.shape[0]  # width, height

    def _extract_detections(self, results: list) -> List[Detection]:
        detections = []
        for res in results:
            boxes = res.boxes
            if boxes is None or len(boxes) == 0:
                continue
            
            class_names = self.config.get("classes", [])
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i].item())
                conf = float(boxes.conf[i].item())
                x1, y1, x2, y2 = map(float, boxes.xyxy[i].tolist())
                
                cls_name = class_names[cls_id] if cls_id < len(class_names) else f"unknown_{cls_id}"
                detections.append(Detection(
                    class_id=cls_id,
                    class_name=cls_name,
                    confidence=conf,
                    bbox=(x1, y1, x2, y2),
                    width=int(x2 - x1),
                    height=int(y2 - y1)
                ))
        return detections

    def _compute_structural_features(
        self, detections: List[Detection], img_w: int, img_h: int
    ) -> StructuralFeatures:
        # 1. Counts per class
        class_counts = {}
        for d in detections:
            class_counts[d.class_name] = class_counts.get(d.class_name, 0) + 1

        # 2. BBox coverage ratio
        total_bbox_area = sum(d.width * d.height for d in detections)
        img_area = img_w * img_h
        coverage_ratio = min(total_bbox_area / img_area, 1.0) if img_area > 0 else 0.0

        # 3. Spatial distribution (quadrants)
        mid_x, mid_y = img_w / 2.0, img_h / 2.0
        quadrants = {"TL": 0, "TR": 0, "BL": 0, "BR": 0}
        for d in detections:
            cx, cy = d.center()
            if cx <= mid_x and cy <= mid_y: quadrants["TL"] += 1
            elif cx > mid_x and cy <= mid_y: quadrants["TR"] += 1
            elif cx <= mid_x and cy > mid_y: quadrants["BL"] += 1
            else: quadrants["BR"] += 1

        # 4. Confidence statistics
        confs = np.array([d.confidence for d in detections], dtype=np.float32) if detections else np.array([0.0])
        confidence_stats = {
            "mean": float(np.mean(confs)),
            "max": float(np.max(confs)),
            "std": float(np.std(confs)),
            "median": float(np.median(confs))
        }

        return StructuralFeatures(
            detections=detections,
            class_counts=class_counts,
            total_objects=len(detections),
            bbox_coverage_ratio=coverage_ratio,
            spatial_distribution=quadrants,
            confidence_stats=confidence_stats
        )