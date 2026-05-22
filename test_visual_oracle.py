import json
import sys
from pathlib import Path
from src.visual_oracle import VisualOracle

with open("configs/config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

# Добавляем baseline-параметры, если их нет в конфиге
cfg.setdefault("visual_oracle", {})
cfg["visual_oracle"].setdefault("baseline_mean_ssim", 0.985)
cfg["visual_oracle"].setdefault("baseline_std_ssim", 0.008)

oracle = VisualOracle(cfg)

# Авто-поиск любого изображения в проекте
test_img = next((f for d in [Path("my_dataset_yolo/images/train"), Path("my_dataset_yolo/images/val"), Path(".")] if d.exists() for f in d.rglob("*.png")), None)
if not test_img:
    print("❌ Изображение не найдено. Поместите любой .png в папку проекта.")
    sys.exit(1)

print(f"🖼 Тестовое изображение: {test_img}")
result = oracle.compare(test_img, test_img)  # Сравнение с самим собой = идеальный baseline
print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))