# src/hybrid_aggregator.py
from __future__ import annotations

import math
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger

from src.cv_core.yolo_inference import StructuralFeatures
from src.visual_oracle import VisualOracleResult
from src.ocr_engine import OCRResult


@dataclass
class AggregationResult:
    """Итоговый результат гибридной агрегации сигналов."""
    final_confidence: float          # Калиброванная вероятность дефекта [0.0, 1.0]
    is_defect: bool                  # Бинарное решение по порогу
    raw_score: float                 # Взвешенная сумма до калибровки
    signal_contributions: Dict[str, float]  # Нормализованные дефект-скоры по модалитетам
    temperature: float               # Применённая температура скейлинга
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "final_confidence": round(self.final_confidence, 4),
            "is_defect": self.is_defect,
            "raw_score": round(self.raw_score, 4),
            "signal_contributions": {k: round(v, 4) for k, v in self.signal_contributions.items()},
            "temperature": round(self.temperature, 4),
            "metadata": self.metadata
        }


class HybridAggregator:
    """
    Мультимодальный агрегатор сигналов дефектов.
    Реализует взвешенный фьюжн, температурный скейлинг для калибровки ECE
    и бинаризацию решений на основе настраиваемого порога.
    """

    def __init__(self, config: Dict[str, Any]):
        self.cfg = config.get("hybrid_aggregator", {})
        self.weights = self.cfg.get("weights", {
            "ssim": 0.35, "psnr": 0.20, "ocr_sim": 0.25,
            "yolo_struct_drift": 0.15, "yolo_bbox_shift": 0.05
        })
        self.threshold = self.cfg.get("defect_confidence_threshold", 0.65)
        self.calibration_method = self.cfg.get("calibration_method", "temperature_scaling")
        
        # Инициализация температуры T=1.0 (без калибровки)
        self.temperature = self.cfg.get("initial_temperature", 1.0)
        self._validate_weights()

    def _validate_weights(self):
        total = sum(self.weights.values())
        if total <= 0:
            raise ValueError("Sum of aggregation weights must be > 0")
        # Нормализация весов до 1.0 для стабильности
        if abs(total - 1.0) > 1e-6:
            logger.warning(f"Normalizing weights from sum={total:.3f} to 1.0")
            self.weights = {k: v / total for k, v in self.weights.items()}
    
    def aggregate_signals(
        self,
        oracle: VisualOracleResult,
        ocr: OCRResult,
        yolo: StructuralFeatures,
        ref_yolo: Optional[StructuralFeatures] = None
    ) -> AggregationResult:
        # Нелинейная нормализация: UI-дефекты усиливаются, фоновый шум гасится
        s_ssim = min(1.0, max(0.0, (1.0 - oracle.ssim_score) * 15.0))  # SSIM 0.95 → 0.75
        s_psnr = min(1.0, max(0.0, (35.0 - oracle.psnr_score) / 8.0))  # PSNR < 30dB → резкий рост
        s_ocr = max(0.0, min(1.0, 1.0 - (ocr.similarity_score or 0.95)))
        
        s_struct, s_bbox = self._compute_yolo_deviation(yolo, ref_yolo)

        signals = {
            "ssim": s_ssim,
            "psnr": s_psnr,
            "ocr_sim": s_ocr,
            "yolo_struct_drift": s_struct,
            "yolo_bbox_shift": s_bbox
        }

        raw_score = sum(self.weights.get(k, 0.0) * v for k, v in signals.items())
        raw_score = max(0.0, min(1.0, raw_score))

        if self.calibration_method == "temperature_scaling":
            final_conf = self._apply_temperature_scaling(raw_score, self.temperature)
        else:
            final_conf = raw_score

        is_defect = final_conf >= self.threshold

        logger.info(
            f"Aggregation | Raw: {raw_score:.4f} | Calib: {final_conf:.4f} | "
            f"Threshold: {self.threshold} | Defect: {is_defect} | T: {self.temperature:.3f}"
        )

        return AggregationResult(
            final_confidence=final_conf,
            is_defect=is_defect,
            raw_score=raw_score,
            signal_contributions=signals,
            temperature=self.temperature,
            metadata={"weights": self.weights}
        )

    def _compute_yolo_deviation(
        self, current: StructuralFeatures, reference: Optional[StructuralFeatures]
    ) -> Tuple[float, float]:
        """
        Вычисляет структурный дрейф и сдвиг bbox относительно референса.
        Исправлено: использует union ключей для корректного сравнения классов.
        """
        if reference is None:
            return 0.0, 0.0

        # 1. Structural drift: Jaccard по class_counts с использованием union ключей
        all_classes = set(current.class_counts.keys()) | set(reference.class_counts.keys())
        if not all_classes:
            struct_drift = 0.0
        else:
            cur_vec = np.array([current.class_counts.get(c, 0) for c in sorted(all_classes)], dtype=float)
            ref_vec = np.array([reference.class_counts.get(c, 0) for c in sorted(all_classes)], dtype=float)
            
            intersection = np.minimum(cur_vec, ref_vec).sum()
            union = np.maximum(cur_vec, ref_vec).sum()
            struct_drift = 1.0 - (intersection / union if union > 0 else 1.0)

        # 2. BBox shift: разница в coverage ratio + пространственное распределение
        cov_shift = abs(current.bbox_coverage_ratio - reference.bbox_coverage_ratio)
        
        # Сравнение распределения по квадрантам (используем все 4 квадранта)
        quad_keys = ["TL", "TR", "BL", "BR"]
        cur_quads = np.array([current.spatial_distribution.get(q, 0) for q in quad_keys], dtype=float)
        ref_quads = np.array([reference.spatial_distribution.get(q, 0) for q in quad_keys], dtype=float)
        
        total_cur = current.total_objects if current.total_objects > 0 else 1
        quad_diff = np.abs(cur_quads - ref_quads).sum() / total_cur
        bbox_shift = 0.5 * cov_shift + 0.5 * min(1.0, quad_diff / 4.0)

        return min(1.0, struct_drift), min(1.0, bbox_shift)

    @staticmethod
    def _apply_temperature_scaling(prob: float, temperature: float) -> float:
        """
        Температурный скейлинг через логит-пространство.
        logit(p) = ln(p/(1-p)), scaled = logit/T, calibrated = sigmoid(scaled)
        """
        eps = 1e-7
        p_clipped = np.clip(prob, eps, 1.0 - eps)
        logit = math.log(p_clipped / (1.0 - p_clipped))
        scaled_logit = logit / temperature
        return float(1.0 / (1.0 + math.exp(-scaled_logit)))

    def fit_temperature(self, val_scores: List[float], val_labels: List[bool], 
                        lr: float = 0.01, epochs: int = 100) -> float:
        """
        Оптимизация температуры T методом минимизации Negative Log Likelihood (NLL).
        """
        T = 1.0
        labels_arr = np.array(val_labels, dtype=float)
        scores_arr = np.array(val_scores, dtype=float)

        for epoch in range(epochs):
            probs = np.array([self._apply_temperature_scaling(s, T) for s in scores_arr])
            # Binary Cross Entropy / NLL
            eps = 1e-7
            nll = -np.mean(labels_arr * np.log(np.clip(probs, eps, 1.0)) + 
                           (1 - labels_arr) * np.log(np.clip(1 - probs, eps, 1.0)))
            
            # Численный градиент по T
            dT = 1e-5
            nll_plus = -np.mean(labels_arr * np.log(np.clip([self._apply_temperature_scaling(s, T + dT) for s in scores_arr], eps, 1.0)) + 
                                (1 - labels_arr) * np.log(np.clip(1 - np.array([self._apply_temperature_scaling(s, T + dT) for s in scores_arr]), eps, 1.0)))
            grad = (nll_plus - nll) / dT
            T -= lr * grad
            T = max(0.1, min(10.0, T))  # Ограничение диапазона

            if epoch % 20 == 0:
                logger.debug(f"Temp fitting epoch {epoch} | T: {T:.4f} | NLL: {nll:.4f}")

        logger.info(f"Temperature optimized: {T:.4f} | Final NLL: {nll:.4f}")
        self.temperature = T
        return T

    @staticmethod
    def compute_ece(confidences: List[float], labels: List[bool], n_bins: int = 10) -> float:
        """
        Expected Calibration Error (ECE).
        """
        if not confidences:
            return 0.0
            
        confs = np.array(confidences)
        labs = np.array(labels, dtype=float)
        bin_bounds = np.linspace(0.0, 1.0, n_bins + 1)
        ece = 0.0

        for b in range(n_bins):
            mask = (confs > bin_bounds[b]) & (confs <= bin_bounds[b+1])
            if mask.sum() == 0:
                continue
            bin_acc = labs[mask].mean()
            bin_conf = confs[mask].mean()
            bin_weight = mask.sum() / len(confs)
            ece += bin_weight * abs(bin_acc - bin_conf)

        return float(ece)