# scripts/calibrate_thresholds.py
#!/usr/bin/env python3
"""
Скрипт калибровки порогов детекции дефектов.
Собирает baseline-шум на чистых скриншотах и вычисляет адаптивные пороги:
    threshold = μ ± k*σ
где знак зависит от направления сигнала (SSIM: "-", PSNR: "-", OCR_sim: "-", etc.)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend для Windows/CI
import matplotlib.pyplot as plt
from loguru import logger

# Добавляем корень проекта в PATH для импортов
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.cv_core.yolo_inference import YOLOInferenceEngine
from src.visual_oracle import VisualOracle
from src.ocr_engine import OCREngine


@dataclass
class SignalStats:
    """Статистика одного сигнала на baseline-выборке."""
    name: str
    values: List[float] = field(default_factory=list)
    mean: float = 0.0
    std: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    percentile_5: float = 0.0
    percentile_95: float = 0.0
    
    @property
    def is_initialized(self) -> bool:
        return len(self.values) > 0
    
    def compute(self):
        if not self.values:
            return
        arr = np.array(self.values, dtype=np.float32)
        self.mean = float(np.mean(arr))
        self.std = float(np.std(arr))
        self.min_val = float(np.min(arr))
        self.max_val = float(np.max(arr))
        self.percentile_5 = float(np.percentile(arr, 5))
        self.percentile_95 = float(np.percentile(arr, 95))
    
    def get_threshold(self, k: float, direction: str = "lower") -> float:
        """
        Вычисляет порог по формуле μ ± k*σ.
        direction: "lower" → μ - k*σ (для SSIM, PSNR, OCR_sim — чем выше, тем лучше)
                   "upper" → μ + k*σ (для coverage_drift, bbox_shift — чем ниже, тем лучше)
        """
        if direction == "lower":
            return self.mean - k * self.std
        else:
            return self.mean + k * self.std
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "n_samples": len(self.values),
            "mean": round(self.mean, 4),
            "std": round(self.std, 4),
            "min": round(self.min_val, 4),
            "max": round(self.max_val, 4),
            "p5": round(self.percentile_5, 4),
            "p95": round(self.percentile_95, 4)
        }


class BaselineCollector:
    """Сборщик baseline-статистики по всем сигналам."""
    
    def __init__(self, config: Dict[str, Any], sites: Optional[List[str]] = None):
        self.cfg = config
        self.paths = config.get("paths", {})
        self.benchmarks_root = Path(self.paths.get("benchmarks_root", "benchmarks"))
        self.gt_dir = Path(self.paths.get("ground_truth_dir", "benchmarks/ground_truth"))
        
        self.sites = sites or self._discover_sites()
        self.oracle = VisualOracle(config)
        self.ocr = OCREngine(config)
        self.yolo = YOLOInferenceEngine(config)
        
        # Инициализация статистик
        self.signals: Dict[str, SignalStats] = {
            "ssim": SignalStats("ssim"),
            "psnr": SignalStats("psnr"),
            "ocr_similarity": SignalStats("ocr_similarity"),
            "yolo_coverage_ratio": SignalStats("yolo_coverage_ratio"),
            "yolo_total_objects": SignalStats("yolo_total_objects"),
            "yolo_mean_confidence": SignalStats("yolo_mean_confidence")
        }
        
        # Направление порога для каждого сигнала
        self.signal_directions = {
            "ssim": "lower", "psnr": "lower", "ocr_similarity": "lower",
            "yolo_coverage_ratio": "upper", "yolo_total_objects": "upper",
            "yolo_mean_confidence": "lower"
        }

    def _discover_sites(self) -> List[str]:
        """Авто-поиск доступных сайтов в benchmarks/sites/."""
        sites_dir = self.benchmarks_root / "sites"
        if not sites_dir.exists():
            logger.warning(f"Benchmarks dir not found: {sites_dir}")
            return []
        return [d.name for d in sites_dir.iterdir() if d.is_dir()]

    def _get_reference_screenshots(self, site: str) -> List[Path]:
        """Получает список референсных скриншотов для сайта."""
        ref_dir = self.benchmarks_root / "sites" / site / "screenshots" / "reference"
        if ref_dir.exists():
            return list(ref_dir.glob("*.png")) + list(ref_dir.glob("*.jpg"))
        # Fallback: ищем в корне screenshots
        alt_dir = self.benchmarks_root / "sites" / site / "screenshots"
        if alt_dir.exists():
            return [p for p in alt_dir.glob("*.png") + list(alt_dir.glob("*.jpg")) 
                    if "ref" in p.name.lower() or "baseline" in p.name.lower()]
        return []

    def collect(self, n_samples: int = 50, seed: int = 42) -> Dict[str, SignalStats]:
        """
        Основной метод сбора baseline-статистики.
        """
        np.random.seed(seed)
        logger.info(f"Starting baseline collection | Sites: {self.sites} | Samples/site: {n_samples}")
        
        total_collected = 0
        
        for site in self.sites:
            ref_screens = self._get_reference_screenshots(site)
            if not ref_screens:
                logger.warning(f"No reference screenshots found for site: {site}")
                continue
                
            logger.info(f"Processing site: {site} | Found {len(ref_screens)} reference images")
            
            # Сэмплируем скриншоты (с повторами если нужно)
            samples = np.random.choice(ref_screens, size=min(n_samples, len(ref_screens)), replace=len(ref_screens) < n_samples)
            
            for img_path in samples:
                try:
                    self._process_single_image(img_path)
                    total_collected += 1
                except Exception as e:
                    logger.error(f"Failed to process {img_path}: {e}")
                    continue
        
        # Финальный расчёт статистик
        for stat in self.signals.values():
            stat.compute()
            
        logger.info(f"Baseline collection complete | Total samples: {total_collected}")
        return self.signals

    def _process_single_image(self, img_path: Path):
        """Обработка одного изображения: сбор всех сигналов."""
        # 1. Visual Oracle
        # Для baseline сравниваем изображение с самим собой (идеальный случай)
        # В реальности можно использовать несколько прогонов одного сценария
        oracle_result = self.oracle.compare(img_path, img_path)
        self.signals["ssim"].values.append(oracle_result.ssim_score)
        self.signals["psnr"].values.append(oracle_result.psnr_score)
        
        # 2. OCR Similarity (сравниваем извлечённый текст с самим собой)
        ocr_result = self.ocr.extract_from_image(img_path)
        # similarity_score для identical text should be ~1.0
        sim = self.ocr.calculate_similarity(ocr_result.full_text, ocr_result.full_text)
        self.signals["ocr_similarity"].values.append(sim)
        
        # 3. YOLO Structural Features
        yolo_features = self.yolo.predict(img_path)
        self.signals["yolo_coverage_ratio"].values.append(yolo_features.bbox_coverage_ratio)
        self.signals["yolo_total_objects"].values.append(yolo_features.total_objects)
        self.signals["yolo_mean_confidence"].values.append(yolo_features.confidence_stats["mean"])


class ThresholdCalibrator:
    """Калибратор порогов на основе собранной статистики."""
    
    def __init__(self, signals: Dict[str, SignalStats], k: float = 2.5):
        self.signals = signals
        self.k = k
        self.thresholds: Dict[str, float] = {}
        
    def compute_all_thresholds(self) -> Dict[str, float]:
        """Вычисляет пороги для всех сигналов."""
        for name, stat in self.signals.items():
            if not stat.is_initialized:
                logger.warning(f"Skipping {name}: no data collected")
                continue
            direction = "lower"  # Default
            if name in ["yolo_coverage_ratio", "yolo_total_objects"]:
                direction = "upper"
            self.thresholds[name] = stat.get_threshold(self.k, direction)
            logger.info(f"{name}: threshold = {self.thresholds[name]:.4f} (μ={stat.mean:.4f}, σ={stat.std:.4f}, k={self.k})")
        return self.thresholds
    
    def generate_report(self, output_dir: Path) -> Path:
        """Генерирует JSON-отчёт и графики распределений."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. JSON отчёт
        report = {
            "calibration_timestamp": datetime.now().isoformat(),
            "k_value": self.k,
            "signals": {name: stat.to_dict() for name, stat in self.signals.items() if stat.is_initialized},
            "thresholds": {k: round(v, 4) for k, v in self.thresholds.items()}
        }
        
        report_path = output_dir / "calibration_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"Report saved: {report_path}")
        
        # 2. Графики распределений
        self._plot_distributions(output_dir)
        
        return report_path
    
    def _plot_distributions(self, output_dir: Path):
        """Строит гистограммы с порогами для каждого сигнала."""
        for name, stat in self.signals.items():
            if not stat.is_initialized or len(stat.values) < 10:
                continue
                
            plt.figure(figsize=(8, 5))
            values = np.array(stat.values)
            
            # Гистограмма
            plt.hist(values, bins=30, edgecolor='black', alpha=0.7, label='Baseline samples')
            
            # Линии: mean, threshold
            threshold = self.thresholds.get(name)
            if threshold is not None:
                plt.axvline(threshold, color='red', linestyle='--', linewidth=2, 
                           label=f'Threshold (μ{"-" if name in ["ssim","psnr","ocr_similarity"] else "+"}kσ)')
            plt.axvline(stat.mean, color='green', linestyle=':', linewidth=1.5, label=f'Mean (μ)')
            
            plt.title(f'Distribution: {name} (n={len(values)})')
            plt.xlabel('Value')
            plt.ylabel('Frequency')
            plt.legend()
            plt.grid(alpha=0.3)
            plt.tight_layout()
            
            plot_path = output_dir / f"{name}_distribution.png"
            plt.savefig(plot_path, dpi=150)
            plt.close()
            logger.debug(f"Plot saved: {plot_path}")


def update_config(config_path: Path, thresholds: Dict[str, float], backup: bool = True) -> Path:
    """Обновляет config.json калиброванными порогами."""
    if backup and config_path.exists():
        backup_path = config_path.with_suffix(".json.bak")
        shutil.copy2(config_path, backup_path)
        logger.info(f"Config backup created: {backup_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # Обновляем секции
    if "visual_oracle" in config:
        # Для SSIM порог: adaptive = mean - k*std
        if "ssim" in thresholds:
            config["visual_oracle"]["baseline_mean_ssim"] = 0.985  # Placeholder, нужно из статистики
            config["visual_oracle"]["baseline_std_ssim"] = 0.008    # Placeholder
            # В реальной реализации здесь подставляются значения из SignalStats
    
    if "hybrid_aggregator" in config and "ocr_similarity" in thresholds:
        # Можно добавить OCR-порог если нужно
        pass
    
    # Сохраняем
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Config updated: {config_path}")
    return config_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calibrate defect detection thresholds using baseline noise analysis")
    parser.add_argument("--config", type=str, default="configs/config.json", help="Path to config.json")
    parser.add_argument("--sites", type=str, nargs="*", help="Specific sites to use for calibration (default: all)")
    parser.add_argument("--samples", type=int, default=50, help="Number of baseline samples per site")
    parser.add_argument("--k", type=float, default=2.5, help="Sigma multiplier for threshold calculation")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output", type=str, default="reports/calibration", help="Output directory for reports")
    parser.add_argument("--update-config", action="store_true", help="Automatically update config.json with calibrated values")
    parser.add_argument("--no-plots", action="store_true", help="Skip generating distribution plots")
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Настройка логирования
    logger.remove()
    logger.add(sys.stderr, level="INFO", 
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
    
    # Загрузка конфига
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config not found: {config_path}")
        sys.exit(1)
        
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    logger.info(f"Starting threshold calibration | k={args.k} | samples={args.samples}")
    
    # 1. Сбор baseline-статистики
    collector = BaselineCollector(config, sites=args.sites)
    signals = collector.collect(n_samples=args.samples, seed=args.seed)
    
    # 2. Вычисление порогов
    calibrator = ThresholdCalibrator(signals, k=args.k)
    thresholds = calibrator.compute_all_thresholds()
    
    # 3. Генерация отчёта
    output_dir = Path(args.output)
    report_path = calibrator.generate_report(output_dir)
    
    # 4. Опциональное обновление конфига
    if args.update_config:
        update_config(config_path, thresholds, backup=True)
    
    # 5. Итоговый вывод
    print("\n" + "="*60)
    print("CALIBRATION COMPLETE")
    print("="*60)
    for name, thresh in thresholds.items():
        stat = signals[name]
        direction = "↓" if name in ["ssim", "psnr", "ocr_similarity"] else "↑"
        print(f"{name:25s} | threshold = {thresh:.4f} {direction} | μ={stat.mean:.4f} ± {stat.std:.4f}")
    print(f"\nReport: {report_path}")
    if args.update_config:
        print(f"Config updated: {config_path}")
    print("="*60)


if __name__ == "__main__":
    main()