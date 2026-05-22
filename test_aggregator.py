# test_aggregator.py
import json
from src.hybrid_aggregator import HybridAggregator
from src.visual_oracle import VisualOracleResult
from src.ocr_engine import OCRResult
from src.cv_core.yolo_inference import StructuralFeatures, Detection

with open("configs/config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

agg = HybridAggregator(cfg)

# Мокаем результаты (в реальности придут из предыдущих модулей)
oracle = VisualOracleResult(ssim_score=0.82, psnr_score=22.5, local_ssim_map=None, 
                            masked_regions_ratio=0.02, is_defect=True, confidence=0.7, 
                            adaptive_threshold=0.9, details={})
ocr = OCRResult(full_text="Login", normalized_full_text="login", blocks=[], 
                avg_confidence=0.95, similarity_score=0.85, is_defect=False, details={})
yolo = StructuralFeatures(detections=[], class_counts={"button": 2, "input": 1}, 
                          total_objects=3, bbox_coverage_ratio=0.15, 
                          spatial_distribution={"TL":1, "TR":2, "BL":0, "BR":0},
                          confidence_stats={"mean":0.8, "max":0.9, "std":0.05, "median":0.8})

res = agg.aggregate_signals(oracle, ocr, yolo)
print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False))

# Тест ECE и калибровки
val_scores = [0.1, 0.3, 0.6, 0.8, 0.9]
val_labels = [False, False, True, True, True]
agg.fit_temperature(val_scores, val_labels)
ece = HybridAggregator.compute_ece(val_scores, val_labels)
print(f"\nOptimized T: {agg.temperature:.4f} | ECE: {ece:.4f}")