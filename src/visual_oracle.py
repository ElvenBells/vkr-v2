# src/visual_oracle.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, Union, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import cv2
from skimage.metrics import structural_similarity as ssim
from loguru import logger


@dataclass
class VisualOracleResult:
    """Результат визуального сравнения двух скриншотов."""
    ssim_score: float
    psnr_score: float
    local_ssim_map: Optional[np.ndarray]
    masked_regions_ratio: float
    is_defect: bool
    confidence: float
    adaptive_threshold: float
    details: Dict[str, Any]

    def to_dict(self) -> dict:
        return {
            "ssim_score": float(round(self.ssim_score, 4)),
            "psnr_score": float(round(self.psnr_score, 2)),
            "masked_regions_ratio": float(round(self.masked_regions_ratio, 4)),
            "is_defect": bool(self.is_defect),  # ← КРИТИЧНО: конвертация numpy.bool_ → bool
            "confidence": float(round(self.confidence, 4)),
            "adaptive_threshold": float(round(self.adaptive_threshold, 4)),
            "details": self.details
        }


class VisualOracle:
    """
    Визуальный оракул для сравнения эталонного и тестового скриншотов.
    Реализует SSIM/PSNR, адаптивный σ-порог и маскирование динамических зон.
    """

    def __init__(self, config: Dict[str, Any]):
        self.cfg = config.get("visual_oracle", {})
        self.paths = config.get("paths", {})
        self._validate_config()
        
        # Базовые пороги и статистика шума (обновляются скриптом калибровки)
        self.baseline_mean_ssim = self.cfg.get("baseline_mean_ssim", 0.985)
        self.baseline_std_ssim = self.cfg.get("baseline_std_ssim", 0.008)
        self.sigma_k = self.cfg.get("sigma_k", 2.5)
        
        self.ignore_padding_pct = self.cfg.get("ignore_roi_padding_pct", 5)
        self.mask_animations = self.cfg.get("mask_animations", True)
        self.animation_diff_threshold = 15  # Пикселей разности для маски
        self.min_animation_blob_area_pct = 0.001  # 0.1% от площади экрана

    def _validate_config(self):
        required = {"sigma_k", "ignore_roi_padding_pct", "mask_animations"}
        missing = required - set(self.cfg.keys())
        if missing:
            logger.warning(f"Missing visual_oracle config keys: {missing}. Using defaults.")

    def compare(self, ref_path: Union[str, Path], test_path: Union[str, Path]) -> VisualOracleResult:
        """
        Основной метод сравнения. Возвращает метрики и флаг дефекта с адаптивным порогом.
        """
        ref_gray, ref_color = self._load_and_preprocess(ref_path)
        test_gray, test_color = self._load_and_preprocess(test_path)

        if ref_gray.shape != test_gray.shape:
            logger.warning("Shapes differ. Resizing test image to match reference.")
            test_gray = cv2.resize(test_gray, (ref_gray.shape[1], ref_gray.shape[0]))
            test_color = cv2.resize(test_color, (ref_color.shape[1], ref_color.shape[0]))

        # 1. Глобальный PSNR (до маскирования, для справки)
        psnr = self._calculate_psnr(ref_color, test_color)

        # 2. ROI обрезка (игнорирование бордеров)
        if self.ignore_padding_pct > 0:
            pad = int(ref_gray.shape[0] * self.ignore_padding_pct / 100.0)
            if pad > 0:
                ref_roi = ref_gray[pad:-pad, pad:-pad]
                test_roi = test_gray[pad:-pad, pad:-pad]
            else:
                ref_roi, test_roi = ref_gray, test_gray
        else:
            ref_roi, test_roi = ref_gray, test_gray

        # 3. SSIM + локальная карта различий
        ssim_score, local_diff = ssim(ref_roi, test_roi, data_range=255, full=True)

        # 4. Маскирование анимаций (если включено)
        if self.mask_animations:
            mask, masked_ratio = self._create_animation_mask(ref_roi, test_roi)
            # Пересчёт SSIM только по немаскированной области
            masked_ref = ref_roi.copy()
            masked_test = test_roi.copy()
            masked_ref[mask == 0] = 0
            masked_test[mask == 0] = 0
            
            # Избегаем деления на ноль при полностью замаскированном изображении
            if np.sum(mask) > 0:
                masked_ssim, _ = ssim(masked_ref, masked_test, data_range=255, full=True)
            else:
                masked_ssim = ssim_score
        else:
            masked_ssim = ssim_score
            masked_ratio = 0.0
            mask = np.ones_like(ref_roi)

        # 5. Адаптивный порог и принятие решения
        adaptive_threshold = self.baseline_mean_ssim - (self.sigma_k * self.baseline_std_ssim)
        is_defect = bool(masked_ssim < adaptive_threshold)
        
        # 6. Калибровка confidence (0.0 - no_defect, 1.0 - critical_defect)
        confidence = self._calculate_defect_confidence(masked_ssim, adaptive_threshold, self.baseline_std_ssim)

        logger.info(
            f"Visual comparison | SSIM: {masked_ssim:.4f} | PSNR: {psnr:.2f} | "
            f"Threshold: {adaptive_threshold:.4f} | Defect: {is_defect} | Masked: {masked_ratio:.2%}"
        )

        return VisualOracleResult(
            ssim_score=masked_ssim,
            psnr_score=psnr,
            local_ssim_map=local_diff if not self.mask_animations else None,
            masked_regions_ratio=masked_ratio,
            is_defect=is_defect,
            confidence=confidence,
            adaptive_threshold=adaptive_threshold,
            details={"ref_shape": ref_gray.shape, "mask_shape": mask.shape if self.mask_animations else None}
        )

    def _load_and_preprocess(self, img_path: Union[str, Path]) -> Tuple[np.ndarray, np.ndarray]:
        path = Path(img_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
            
        img_color = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img_color is None:
            raise ValueError(f"Failed to decode image: {path}")
            
        img_gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)
        return img_gray, img_color

    def _calculate_psnr(self, ref: np.ndarray, test: np.ndarray) -> float:
        try:
            return cv2.PSNR(ref, test)
        except Exception:
            return 0.0  # Fallback for identical or invalid shapes

    def _create_animation_mask(self, ref_roi: np.ndarray, test_roi: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Создает маску динамических регионов на основе попиксельной разности.
        Игнорирует мелкие шумовые блоки и изолированные артефакты.
        """
        diff = cv2.absdiff(ref_roi, test_roi)
        _, diff_bin = cv2.threshold(diff, self.animation_diff_threshold, 255, cv2.THRESH_BINARY)
        
        # Морфологическое сглаживание для удаления шума
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        diff_clean = cv2.morphologyEx(diff_bin, cv2.MORPH_OPEN, kernel, iterations=2)
        
        # Поиск связных компонентов
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(diff_clean, connectivity=8)
        
        mask = np.ones_like(ref_roi)
        img_area = ref_roi.shape[0] * ref_roi.shape[1]
        min_area = int(img_area * self.min_animation_blob_area_pct)
        
        masked_pixels = 0
        for i in range(1, num_labels):  # 0 - фон
            area = stats[i, cv2.CC_STAT_AREA]
            if area < min_area:
                mask[labels == i] = 0
                masked_pixels += area
                
        return mask, masked_pixels / img_area

    def _calculate_defect_confidence(self, actual_ssim: float, threshold: float, std_ssim: float) -> float:
        """
        Маппинг отклонения от порога в confidence [0.0, 1.0].
        Если ssim >= threshold → 0.0 (нет дефекта)
        Если ssim < threshold → растет экспоненциально с удалением от порога.
        """
        if actual_ssim >= threshold:
            return 0.0
            
        deviation = (threshold - actual_ssim) / (std_ssim if std_ssim > 0 else 0.01)
        # Sigmoid-подобное масштабирование для плавного роста
        confidence = 1.0 / (1.0 + np.exp(-1.5 * (deviation - 1.0)))
        return float(np.clip(confidence, 0.0, 1.0))