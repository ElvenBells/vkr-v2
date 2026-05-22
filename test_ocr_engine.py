import json
import sys
from pathlib import Path
from src.ocr_engine import OCREngine

with open("configs/config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

engine = OCREngine(cfg)

test_img = next((f for d in [Path("my_dataset_yolo/images/train"), Path("my_dataset_yolo/images/val"), Path(".")] if d.exists() for f in d.rglob("*.png")), None)
if not test_img:
    print("❌ Изображение не найдено.")
    sys.exit(1)

res = engine.extract_from_image(test_img)
print(json.dumps(res.to_dict(), indent=2, ensure_ascii=False)[:500] + "...")
print(f"\n✅ Similarity test: {OCREngine.calculate_similarity('Войти в аккаунт', 'войти в аккаунт!'):.4f}")