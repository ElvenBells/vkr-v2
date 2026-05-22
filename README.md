# CV-AI Web Test Automation Framework

Автоматизированная система тестирования frontend'а с использованием компьютерного зрения, OCR и гибридной агрегации сигналов. Разработана для повышения устойчивости тестов к рефакторингу верстки и снижения False Positives.

## 🛠 Требования
- Python 3.10+
- Tesseract OCR: `sudo apt install tesseract-ocr` (Linux) / `brew install tesseract` (macOS)
- Playwright browsers: `playwright install`

## 🚀 Быстрый старт
```bash
# 1. Клонирование и окружение
git clone <repo> && cd cv-ai-test-automation
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Установка браузеров
playwright install chromium

# 3. Размещение модели
mkdir -p models && cp path/to/best.pt models/best.pt

# 4. Калибровка порогов (опционально, но рекомендовано)
python scripts/calibrate_thresholds.py --baseline-runs 50

# 5. Запуск экспериментов
python scripts/run_experiment.py --sites all --defects all --mode cv,pw