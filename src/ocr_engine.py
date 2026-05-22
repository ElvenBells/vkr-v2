# src/ocr_engine.py
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
import cv2
import numpy as np
import pytesseract
import Levenshtein
from loguru import logger


@dataclass
class OCRBlock:
    """Единичный текстовый блок, распознанный Tesseract."""
    text: str
    normalized: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "normalized": self.normalized,
            "confidence": round(self.confidence, 2),
            "bbox": self.bbox
        }


@dataclass
class OCRResult:
    """Итоговый результат OCR-анализа скриншота."""
    full_text: str
    normalized_full_text: str
    blocks: List[OCRBlock]
    avg_confidence: float
    similarity_score: Optional[float] = None
    is_defect: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "full_text": self.full_text,
            "normalized_full_text": self.normalized_full_text,
            "blocks": [b.to_dict() for b in self.blocks],
            "avg_confidence": float(round(self.avg_confidence, 2)),
            "similarity_score": float(round(self.similarity_score, 4)) if self.similarity_score is not None else None,
            "is_defect": bool(self.is_defect),
            "details": self.details
        }


class OCREngine:
    """
    Обёртка над Tesseract OCR для извлечения и валидации текста на UI-скриншотах.
    Поддерживает полную обработку, ROI-вырезку, нормализацию и сравнение по Левенштейну.
    """

    def __init__(self, config: Dict[str, Any]):
        self.cfg = config.get("ocr", {})
        self.paths = config.get("paths", {})
        self.lang = self.cfg.get("lang", "rus+eng")
        self.tess_config = self.cfg.get("config", "--psm 6 --oem 3")
        self.min_confidence = self.cfg.get("min_text_confidence", 0.6)
        self.lev_tol = self.cfg.get("levenshtein_tolerance", 2)

        self._setup_tesseract_path()
        self._validate_tesseract()

    def _setup_tesseract_path(self):
        """Универсальный поиск Tesseract для Windows/Linux/macOS."""
        explicit_path = self.cfg.get("tesseract_cmd")
        if explicit_path and Path(explicit_path).exists():
            pytesseract.pytesseract.tesseract_cmd = explicit_path
            logger.info(f"Tesseract loaded from config: {explicit_path}")
            return

        # 1. Проверка переменных окружения
        for env_var in ["TESSERACT_CMD", "TESSERACT_PATH"]:
            env_path = os.environ.get(env_var)
            if env_path and Path(env_path).exists():
                pytesseract.pytesseract.tesseract_cmd = env_path
                logger.info(f"Tesseract loaded from ENV {env_var}: {env_path}")
                return

        # 2. Стандартные пути Windows
        win_paths = [
            Path(os.environ.get("PROGRAMFILES", "")) / "Tesseract-OCR" / "tesseract.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Tesseract-OCR" / "tesseract.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / "tesseract.exe",
        ]
        for p in win_paths:
            if p.exists():
                pytesseract.pytesseract.tesseract_cmd = str(p)
                logger.info(f"Auto-detected Tesseract: {p}")
                return

        # 3. Fallback: проверка системного PATH
        try:
            import subprocess
            subprocess.run(["tesseract", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            pytesseract.pytesseract.tesseract_cmd = "tesseract"
            logger.info("Tesseract found in system PATH")
            return
        except Exception:
            pass

        raise RuntimeError(
            "❌ Tesseract OCR не найден.\n"
            "💡 Решение:\n"
            "  1. Установите Tesseract: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "  2. Укажите полный путь в config.json -> ocr.tesseract_cmd\n"
            "  3. Или добавьте папку с tesseract.exe в системную переменную PATH"
        )

    def _validate_tesseract(self):
        try:
            ver = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract OCR initialized | Version: {ver} | Lang: {self.lang}")
        except Exception as e:
            raise RuntimeError(
                f"❌ Tesseract initialization failed: {e}\n"
                "💡 Решение: установите Tesseract-OCR и добавьте в PATH, либо укажите 'tesseract_cmd' в config.json"
            ) from e

    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """Подготовка изображения для Tesseract: градации серого + мягкое сглаживание."""
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        # FastNlMeansDenoising сохраняет края текста, убирая артефакты сжатия
        denoised = cv2.fastNlMeansDenoising(gray, h=3, templateWindowSize=7, searchWindowSize=21)
        return denoised

    def _normalize_text(self, text: str) -> str:
        """Нормализация: удаление пунктуации, приведение к нижнему регистру, схлопывание пробелов."""
        if not text:
            return ""
        # Unicode-aware очистка
        cleaned = re.sub(r'[^\w\s]', '', text, flags=re.UNICODE)
        cleaned = cleaned.lower().strip()
        return re.sub(r'\s+', ' ', cleaned)

    def _extract_blocks(self, processed_img: np.ndarray) -> List[OCRBlock]:
        """Распознавание текста на уровне слов/строк с фильтрацией по confidence."""
        data = pytesseract.image_to_data(
            processed_img, 
            lang=self.lang, 
            config=self.tess_config, 
            output_type=pytesseract.Output.DICT
        )
        
        blocks = []
        n_boxes = len(data.get('text', []))
        for i in range(n_boxes):
            text = data['text'][i].strip()
            conf = float(data['conf'][i])
            
            if text and conf >= self.min_confidence:
                bbox = (
                    int(data['left'][i]), 
                    int(data['top'][i]), 
                    int(data['width'][i]), 
                    int(data['height'][i])
                )
                blocks.append(OCRBlock(
                    text=text,
                    normalized=self._normalize_text(text),
                    confidence=conf,
                    bbox=bbox
                ))
        return blocks

    def extract_from_image(self, image_path: Union[str, Path]) -> OCRResult:
        """Полный OCR-анализ изображения."""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
            
        img = cv2.imread(str(path))
        if img is None:
            raise ValueError(f"Failed to decode image: {path}")
            
        return self._process_internal(img, ref_text=None)

    def extract_from_roi(self, image_path: Union[str, Path], bbox: Tuple[int, int, int, int]) -> OCRResult:
        """OCR-анализ только указанной области (x, y, w, h)."""
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Failed to decode image: {image_path}")
            
        x, y, w, h = bbox
        roi = img[y:y+h, x:x+w]
        if roi.size == 0:
            raise ValueError(f"Invalid ROI bbox: {bbox} for image shape: {img.shape}")
            
        return self._process_internal(roi, ref_text=None)

    def _process_internal(self, img: np.ndarray, ref_text: Optional[str]) -> OCRResult:
        """Внутренний пайплайн: препроцесс → распознавание → сравнение."""
        processed = self._preprocess_image(img)
        blocks = self._extract_blocks(processed)
        
        full_text = " ".join(b.text for b in blocks)
        norm_full = self._normalize_text(full_text)
        avg_conf = float(np.mean([b.confidence for b in blocks])) if blocks else 0.0

        sim_score = None
        is_def = False
        if ref_text is not None:
            sim_score = self.calculate_similarity(ref_text, norm_full)
            dist = Levenshtein.distance(self._normalize_text(ref_text), norm_full)
            is_def = dist > self.lev_tol

        logger.info(
            f"OCR Processed | Blocks: {len(blocks)} | AvgConf: {avg_conf:.2f} | "
            f"Sim: {sim_score} | Defect: {is_def} | ROI: {img.shape[1]}x{img.shape[0]}"
        )

        return OCRResult(
            full_text=full_text,
            normalized_full_text=norm_full,
            blocks=blocks,
            avg_confidence=avg_conf,
            similarity_score=sim_score,
            is_defect=is_def,
            details={"image_shape": img.shape, "preprocessed_shape": processed.shape}
        )

    @staticmethod
    def calculate_similarity(ref_text: str, test_text: str) -> float:
        """
        Возвращает коэффициент схожести текстов [0.0, 1.0] через нормализованное расстояние Левенштейна.
        """
        # Нормализация уже выполнена до вызова, но на всякий случай дублируем
        n_ref = OCREngine._normalize_text_static(ref_text)
        n_test = OCREngine._normalize_text_static(test_text)
        
        if not n_ref and not n_test:
            return 1.0
        if not n_ref or not n_test:
            return 0.0
            
        return Levenshtein.ratio(n_ref, n_test)

    @staticmethod
    def _normalize_text_static(text: str) -> str:
        if not text: return ""
        cleaned = re.sub(r'[^\w\s]', '', text, flags=re.UNICODE)
        return re.sub(r'\s+', ' ', cleaned.lower().strip())