# test_yolo_inference.py
import json
from src.cv_core.yolo_inference import YOLOInferenceEngine

with open("configs/config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

engine = YOLOInferenceEngine(cfg)
# Замените на путь к реальному скриншоту из вашего датасета
result = engine.predict("benchmarks/sites/ecommerce/screenshots/home_page.png")
print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))